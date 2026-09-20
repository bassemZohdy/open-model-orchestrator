# Runtime operations

OMO is a self-hosted open-source distribution. The project does not operate a
production host or provide a managed multi-tenant service. The default
deployment is a private, single-process service. Existing `OMO_API_KEY`
authentication is still supported. Multi-caller access is opt-in through a
local YAML policy; bearer tokens are represented only by SHA-256 hashes.

## Caller policy

Copy [`config/access.example.yaml`](../config/access.example.yaml), replace the
disabled example entry with owner-generated hashes, and set:

```bash
export OMO_ACCESS_POLICY_PATH=config/access.yaml
```

An enabled caller with external budget must list exact provider hostnames in
`allowed_hosts`. Retention is filtered against the registry entry, and the
per-caller daily budget is enforced by bounded reservations. For local restart
durability, set `OMO_BUDGET_DB_PATH` to a dedicated SQLite file. SQLite
transactions are safe for processes on one node. A horizontally scaled
operator may replace this with a managed ledger and provider reconciliation;
that deployment integration is not required for the self-hosted OMO release.

Only a caller with `role: admin` may reload the registry when access-policy
authentication is enabled. Keep the policy file outside the image and never
commit a bearer token.

## Registry administration

The registry is read from the configured local path only; there is no request-
time URL discovery or download. This keeps the published image deterministic;
the operator owns any registry-file distribution or refresh process. Enable
administration explicitly:

```bash
export OMO_REGISTRY_RELOAD_ENABLED=true
```

Authenticated administrators can inspect `GET /admin/registry/status` and
invoke `POST /admin/registry/reload`. Reload validates a complete immutable
snapshot before swapping it. A failed reload keeps the last-known-good
snapshot and exposes only a bounded error type. The status freshness threshold
is controlled by `OMO_REGISTRY_MAX_AGE_SECONDS`.

External model entries declare the currently supported
`utf8-byte-upper-bound` tokenizer strategy. It is a conservative count for
eligibility and cost estimation, not a provider billing statement. Add a
provider-specific tokenizer only with verified bounds and tests.

Runtime metrics contain action/error counters only; prompts, completions, keys,
tenant content and training data are not exported. Operators are responsible
for deployment-level DNS, IP and network egress policy when their environment
requires it.
