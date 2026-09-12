import "@typespec/json-schema";
using TypeSpec.JsonSchema;

namespace FiduciaLeasePolicy;

@id("LeasePolicyV1")
model LeasePolicyV1 {
  @minValue(1)
  @maxValue(1)
  version: integer;

  @minLength(1)
  @maxLength(128)
  resource: string;

  @minValue(1)
  @maxValue(86400)
  lease_ttl_seconds: integer;

  @minValue(1)
  @maxValue(7)
  quorum: integer;

  renewable?: boolean;
}
