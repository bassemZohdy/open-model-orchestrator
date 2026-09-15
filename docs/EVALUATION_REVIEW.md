# Evaluation audit and human review

Evaluation evidence is accepted only as an immutable, reviewable bundle. The
bundle links:

- a source audit record with SPDX license identifier, provenance summary,
  license status and reviewer identity;
- one fixed-provider batch with exact dataset, model, policy and provider
  revisions; and
- optional human-review records that reference prompt IDs without copying raw
  prompt text or credentials.

The evaluation/audit.py module validates these links and produces a selective
risk/coverage calibration report from the existing bounded confidence field.
Confidence is an observation for analysis only; it never authorizes a route or
overrides deterministic policy.

## Review protocol

Use protocol version omo-human-review-v1. For each sampled prompt, the reviewer
checks only the criteria applicable to that case:

1. selection_correct: the observed action matches the expected routing action;
2. arguments_faithful: typed helper arguments match exactly, including signs,
   precision, units and values;
3. result_faithful: the returned result matches the trusted helper/provider
   outcome and is not silently rewritten; and
4. policy_respected: local-only, capability, cost, retention and rejection
   constraints were preserved.

Record pass only when every applicable criterion is true. Record fail only when
at least one applicable criterion is false. Use needs-review when the record
cannot be decided. Include a concise comment for an exception or uncertain case.
Reviewers must not approve an entire corpus from a confidence score or from
repeated copies of one prompt family.

The bundle validator rejects mixed model/policy lineage, duplicate prompt or
review IDs, unknown review prompts, unreviewed approved licenses, and
inconsistent review decisions. Live provider calls, protected-test evaluation,
credential storage, automatic promotion and publication remain outside this
offline contract.
