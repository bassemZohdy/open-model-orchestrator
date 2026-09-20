# Remaining OMO work

Only unfinished work is listed here. Completed repository work belongs in
[`CHANGELOG.md`](CHANGELOG.md). Paid training/inference, external publication,
scheduling and automatic promotion remain disabled.

Task state separates repository implementation from owner-controlled activation.
No `ready` item authorizes paid compute, account changes, publication,
promotion or production deployment.

## Planned model and image lifecycle

GitHub remains the source of truth for code, schemas, tests and manually
dispatched automation. Hugging Face Hub will hold immutable dataset/model
revisions, and Docker Hub will hold the deployable multi-platform runtime image.
Dataset, model and application-image releases remain separate: an application
or dataset change must never schedule training or automatically advance a model
or Docker tag.

The intended promotion chain is:

1. approve an immutable dataset revision and exact base-model revision;
2. manually dispatch a budget-bounded training run;
3. persist the candidate model, lineage and evaluation evidence;
4. independently approve one exact model revision and checksum;
5. build and test the bundled application image with that pinned model; and
6. publish and promote verified image digests.

| ID | Priority / state | Remaining acceptance criteria | Blocker |
|---|---|---|---|
| OMO-002 | P0 / partial; release blocked | Complete independent sandbox/native-parser review and resolve the remaining container findings, or record an owner-approved VEX. | Independent review, VEX approval, clean audit and VM-grade isolation are external gates. |
| OMO-003 | P1 / partial; evidence blocked | Run the pinned five-role model comparison, including the Transformers CPU reference, only after license, hardware and budget approval. | Full sweeps and any provider evaluation require owner approval. |
| OMO-004 | P1 / partial; evidence blocked | Run the held-out evaluator on a reviewed immutable corpus and produce calibration and human-reviewed evidence. | The current evaluator is offline harness coverage, not quality evidence. |
| OMO-006 | P1 / partial; publication blocked | Configure publishing authority/trusted-publisher claims, create or verify the immutable dataset repository, and publish the reviewed original data. The model repository exists but contains no approved OMO fine-tune; never relabel upstream weights. | Dataset repository, publishing scope, license review and immutable upload authority remain owner-controlled. |
| OMO-007 | P0 / blocked stable publication | Resolve the DiskCache/security findings or approve the VEX, verify SBOM/provenance/signatures, and perform evidence-bound multi-platform promotion with rollback manifests. | Docker Hub push permission, protected release environment, signing authority and clean/approved security evidence. |
| OMO-008 | P1 / preparation complete; execution blocked | Implement and validate the isolated Transformers/TRL SFT, full-versus-adapter comparison, export and quantization runner for `omo-routing-proposal-v1`. | Reviewed corpus, locked training stack, protected environment and owner-approved budget. |
| OMO-009 | P1 / partial; evidence blocked | Complete fixed-provider baselines, selective calibration, source/license audit and human review on the enlarged corpus. | Live calls, human review and promotion require approval. |
| OMO-010 | P2 / blocked deployment | Replace local SQLite/in-memory budget reservations with a managed multi-instance ledger, reconcile provider cost and enforce deployment DNS/IP egress policy. | Requires a selected production platform and deployment controls. |
| OMO-011 | P2 / blocked integration | Add an owner-controlled authenticated registry source and refresh integration; add provider tokenizers only with verified bounds and tests. | Request-time discovery/downloads remain intentionally disabled until deployment integration is approved. |
| OMO-013 | P0 / partial; review/Hub blocked | Complete human review and quality/license approval for the 52-record corpus, then publish an immutable dataset revision. | Bootstrap labels, dataset publication authority and review process. |
| OMO-014 | P1 / partial; activation blocked | Keep the manual-only preflight and activate a real isolated job only after all lineage, budget, credential and review gates pass. | HF Jobs eligibility, protected `training` environment, scoped credentials and approved spend. |
| OMO-015 | P1 / repository contract complete; publication blocked | Validate every candidate bundle with the OMO-015 artifact contract, then persist safetensors, tokenizer/template, configuration, lineage, metrics, model card, license provenance and rollback metadata; publish immutable revisions before any alias. | Candidate creation depends on OMO-003, OMO-004, OMO-008, OMO-009 and OMO-014; Hub publication still depends on OMO-006 authority. |
| OMO-016 | P0 / partial; artifact blocked | The disabled model-promotion manifest and trusted build-time materialization/verification path are implemented. Activate them only for an approved fine-tuned revision, then bundle it and retain the upstream rollback target. | Depends on an approved OMO model revision and passed protected evaluation. |
| OMO-017 | P0 / partial; stable delivery blocked | The protected release already produces native AMD64/ARM64 candidates with SBOM/provenance and identity-bound manifests. Add signature verification and stable multi-platform promotion only after OMO-007 and OMO-016 pass. | Depends on the security/VEX decision, signing authority, approved model artifact and protected Docker publication. |
| OMO-018 | P2 / pending operations | Add evidence retention, job/cost capture, candidate comparison, approval audit trail, rollback drill, tag retention and explicit drift/retraining criteria. | Requires one completed OMO-014 through OMO-017 cycle and production-like evidence. |

## External unblocking checklist

These gates cannot be satisfied by repository code alone:

| Gate | Owner-controlled action | Tasks unblocked |
|---|---|---|
| HF resources | Verify the existing model repository, create/verify the dataset repository, confirm licenses/visibility and configure repository-scoped Trusted Publisher claims. | OMO-006, OMO-013, OMO-015 |
| Training budget | Approve one hardware flavor, timeout and maximum cost; enable eligible HF Jobs credits. | OMO-008 execution, OMO-014 activation |
| GitHub environments | Protect `training` and `release`, require reviewers and restrict allowed branches. | OMO-007, OMO-014, OMO-017 |
| Docker Hub publication | Confirm the automation credential can push to `bzohdy/open-model-orchestrator`; login alone is insufficient. | OMO-007, OMO-017 |
| Security/signing | Approve/reject the scoped DiskCache VEX, select signing authority and obtain independent native-parser/sandbox review. | OMO-002, OMO-007 |
