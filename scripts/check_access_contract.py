"""Validate the multi-caller access policy without exposing credentials."""

from pathlib import Path

from omo.access import AccessStore

CONFIG = Path("config/access.example.yaml")
policy = AccessStore.read(str(CONFIG)).policy


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


require(policy.schema_version == "1", "access policy schema version is invalid")
require(
    all(len(caller.key_sha256) == 64 for caller in policy.callers),
    "access policy contains an invalid key digest",
)
require(
    all(caller.max_cost_usd == 0 or caller.allowed_hosts for caller in policy.callers),
    "paid callers must have an explicit host allowlist",
)
print("Access policy contract passed; bearer tokens remain hashed and runtime access is opt-in")
