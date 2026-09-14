import assert from 'node:assert/strict';
import test from 'node:test';

const SHA = '5dbda2127357b4be87821902d36e4ce9560f6876';
const BASE = `https://raw.githubusercontent.com/ORESoftware/ores-interfaces/${SHA}/contracts/ores-compose-machine/v1`;
async function get(path) {
  const r = await fetch(`${BASE}/${path}`);
  assert.equal(r.status, 200, path);
  return r.text();
}
const [schemaText, tsp] = await Promise.all([get('authored.schema.json'), get('main.tsp')]);
const defs = JSON.parse(schemaText).$defs;

test('machine admission identity is project session service revision plus rebuild only', () => {
  assert.deepEqual(Object.keys(defs.EnsureRequest.properties).sort(), ['schema_version','project','session','service','revision','rebuild'].sort());
  assert.equal(defs.EnsureRequest.additionalProperties, false);
});

test('switch fencing is an explicit cross-runtime generation contract', () => {
  assert.equal(defs.ActiveSystem.properties.generation.type, 'string');
  assert.match(tsp, /generation:\s*string/);
  const codes = defs.MachineErrorResponse.properties.code.anyOf.map((x) => x.const);
  assert.ok(codes.includes('stale_generation'));
});

test('serialized machine execution does not expose consensus or lock internals', () => {
  for (const field of ['raft_term','leader_id','lease_token','fencing_token','lock_key','consul_index','etcd_revision']) {
    assert.equal(defs.ActiveSystem.properties[field], undefined, field);
    assert.equal(defs.EnsureRequest.properties[field], undefined, field);
  }
});

test('machine ingress is local-facing and not a distributed-service backend address', () => {
  const p = new RegExp(defs.MachineIngress.properties.authority.pattern);
  assert.ok(p.test('127.0.0.1:39090'));
  assert.equal(p.test('10.10.0.21:7000'), false);
  assert.equal(p.test('172.20.0.5:2379'), false);
});

test('queue busy activation and ingress failures are separately typed', () => {
  const codes = defs.MachineErrorResponse.properties.code.anyOf.map((x) => x.const);
  for (const code of ['queue_full','machine_busy','activation_failed','ingress_unavailable']) assert.ok(codes.includes(code), code);
});
