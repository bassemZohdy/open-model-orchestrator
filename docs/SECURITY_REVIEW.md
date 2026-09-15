# Security review status

This is a review record for the OMO-002 hardening work. It is not a clean
audit, a VEX approval, or a claim of VM-grade isolation.

## Automated controls

- scripts/check_security_report.py preserves every HIGH/CRITICAL Trivy
  finding, reports findings without a fixed version, and fails strict release
  validation when any finding exists. No finding is placed on an ignore list.
- The Monty regression suite covers filesystem, /proc, environment, socket,
  DNS, subprocess, FFI, imports, state reuse, recursion, output, allocation,
  worker crash, cancellation, descriptor inheritance and secret inheritance.
- The llama worker validates JSON protocol shape, rejects unknown request
  fields and duplicate keys, handles malformed UTF-8/surrogates, bounds roles,
  message sizes and aggregate input bytes, and validates output-token bounds and
  optional grammar schema types before invoking the native parser.

## Remaining blockers

Native container findings and the transitive DiskCache advisory still require
owner-approved reachability/VEX review or upstream fixes. The scoped, pending VEX
record is [docs/evidence/diskcache-vex.json](evidence/diskcache-vex.json); it does
not change the strict release disposition. The native parser and
Monty runtime remain part of the trusted computing base. An independent
security review and broader malformed native-input fuzzing are still required
before publication. The release workflow therefore remains private and strict
security mode remains fail-closed.
