import json
import pathlib
import subprocess
import tempfile
import tomllib
import unittest

SOURCE_REPO = "https://github.com/fiducia-cloud/fiducia-infra.git"
SOURCE_SHA = "d1327f6aed1444c5073087ec9d11062230b3cc62"
ENVIRONMENTS = ("preview", "staging", "production")

def run(*args: str, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

class CounterpartInfraLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="fiducia-infra-contract-")
        cls.root = pathlib.Path(cls._tmp.name) / "infra"
        cls.root.mkdir()
        run("git", "init", "-q", cwd=cls.root)
        run("git", "remote", "add", "origin", SOURCE_REPO, cwd=cls.root)
        run("git", "fetch", "--depth=1", "origin", SOURCE_SHA, cwd=cls.root)
        run("git", "checkout", "--detach", "FETCH_HEAD", cwd=cls.root)
        cls.manifest = tomllib.loads((cls.root / ".ores-infra.toml").read_text())

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_modules_first_provider_roots(self) -> None:
        self.assertEqual(self.manifest["schema_version"], 1)
        self.assertEqual(self.manifest["layout"], "modules")
        self.assertEqual(self.manifest["modules_root"], "modules")
        self.assertEqual(self.manifest["environments_root"], "environments")
        providers = self.manifest["providers"]
        self.assertEqual(providers["supabase"]["canonical_path"], "modules/supabase")
        self.assertEqual(providers["supabase"]["native_working_directory"], "modules")
        self.assertEqual(providers["cloudflare"]["canonical_path"], "modules/cloudflare")
        self.assertEqual(providers["neon"]["project_root"], "modules/neon")
        self.assertEqual(providers["neon"]["config"], "modules/neon/neon.ts")
        self.assertEqual(self.manifest["policy"]["state_isolation"], "per-provider-per-environment")

    def test_environment_roots_and_terraform(self) -> None:
        run("terraform", "fmt", "-check", "-recursive", "modules/cloudflare/terraform", cwd=self.root)
        for environment in ENVIRONMENTS:
            env_root = self.root / "environments" / environment
            main_tf = env_root / "main.tf"
            self.assertTrue(main_tf.is_file(), main_tf)
            text = main_tf.read_text()
            self.assertIn('backend "s3" {}', text)
            self.assertIn('source = "../../modules/cloudflare/terraform/worker-shell"', text)
            self.assertIn(f'environment = "{environment}"', text)
            run("terraform", "fmt", "-check", "-recursive", ".", cwd=env_root)
            run("terraform", "init", "-backend=false", "-input=false", cwd=env_root)
            run("terraform", "validate", "-no-color", cwd=env_root)

    def test_durable_object_binding_export_parity(self) -> None:
        wrangler_path = self.root / "modules" / "cloudflare" / "durable-coordinator" / "wrangler.jsonc"
        wrangler = json.loads(wrangler_path.read_text())
        binding = wrangler["durable_objects"]["bindings"][0]
        class_name = binding["class_name"]
        self.assertEqual(binding["name"], "COORDINATOR")
        self.assertEqual(wrangler["exports"][class_name]["type"], "durable-object")
        self.assertEqual(wrangler["exports"][class_name]["storage"], "sqlite")
        for environment in ENVIRONMENTS:
            env_binding = wrangler["env"][environment]["durable_objects"]["bindings"][0]
            self.assertEqual(env_binding["name"], "COORDINATOR")
            self.assertEqual(env_binding["class_name"], class_name)

if __name__ == "__main__":
    unittest.main()
