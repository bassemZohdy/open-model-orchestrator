"""Validate the multi-caller access policy without exposing credentials."""

from pathlib import Path

from omo.access import AccessStore

CONFIG = Path("config/access.example.yaml")
policy = AccessStore.read(str(CONFIG)).policy
assert policy.schema_version == "1"
assert all(len(caller.key_sha256) == 64 for caller in policy.callers)
assert all(caller.max_cost_usd == 0 or caller.allowed_hosts for caller in policy.callers)
print("Access policy contract passed; bearer tokens remain hashed and runtime access is opt-in")
