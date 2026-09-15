# Remaining OMO work

Only unfinished work is listed here. Completed implementation history belongs in
`CHANGELOG.md`. Paid training/inference, external publication, scheduling and
automatic promotion remain disabled.

Task states distinguish implementation readiness from external activation.
`ready` means repository work can proceed now; it does not authorize paid
compute, account changes, publication, promotion or production deployment.

## Planned model and image lifecycle

GitHub remains the source of truth for code, schemas, tests and manually
dispatched automation. Hugging Face Hub will hold the immutable training
dataset and the OMO fine-tuned model; Docker Hub will hold the deployable
multi-platform runtime image. The first OMO-trained artifact will fine-tune the
selected tiny generative base for structured routing/classification proposals.
It will not replace deterministic policy authorization, and an additional
encoder-only classifier will not be added unless a measured comparison proves
that its extra runtime and release lifecycle are justified.

The intended promotion chain is:

1. approve an immutable dataset revision and exact base-model revision;
2. manually dispatch a budget-bounded training run;
3. persist the candidate model, lineage and evaluation evidence on Hugging Face;
4. independently approve one exact model revision and checksum;
5. build and test the bundled application image with that pinned model; and
6. publish and promote verified image digests in Docker Hub.

Dataset, model and application-image releases remain separate. A dataset or
application change must never schedule training or automatically advance a
model or Docker tag.

| ID | Priority / state | Task and acceptance criteria | Dependencies / blocker |
|---|---|---|---|
| OMO-002 | P0 / implementation ready; release blocked | Complete broader malformed native-parser review and prepare a scoped VEX for the DiskCache advisory; obtain independent sandbox review and resolve remaining container HIGH/CRITICAL findings. Retain private deployment restrictions until gates pass. | Parser regression work and VEX evidence gathering can proceed. Independent review, owner VEX approval, clean-audit status and VM-grade isolation remain external release gates. |
| OMO-003 | P1 / benchmark preparation ready | Add reproducible runners for the pinned 360M, Granite, LFM and Qwen comparison plus a Transformers CPU reference; evaluate Q4/Q8 only after the reference comparison and expand the exact local envelope only on evidence. | Open-source harness work can proceed. Full sweeps, LFM license acceptance and paid-provider evaluation remain unapproved. |
| OMO-004 | P1 / partial (offline evaluator complete; evidence blocked) | The repository now validates four held-out routing scenarios covering helper selection, exact argument fidelity, result interpretation and policy-owned routing contention, with category-level scoring and fail-closed missing/unknown observation checks. | A reviewed immutable revision, enlarged corpus, calibration, human-reviewed evidence and any live-provider comparison remain external or future evidence gates. |
| OMO-006 | P1 / blocked account | Obtain HF publishing authority/trusted-publisher claims, create `BassemZohdy/open-model-orchestrator` and `BassemZohdy/open-model-orchestrator-dataset` after exact identity/license checks, and upload original data with immutable revisions. Do not relabel base weights as an OMO fine-tune. | Both Hub resources are currently absent. The current connector is read-only for repositories, so no creation or upload was attempted. |
| OMO-007 | P0 / remediation ready; publication blocked | Make `bzohdy/open-model-orchestrator` an operational Docker Hub release target, not a documentation-only reference: prepare a scoped DiskCache VEX/remediation decision; verify candidate SBOM/provenance and strict vulnerability gates; add signatures and stable multi-platform promotion with rerunnable rollback manifests. Stable aliases advance only after both candidate digests pass. | The current strict audit confirms CVE-2025-69872 has no fixed release and is pulled only by `llama-cpp-python`; technical remediation/signing work can proceed. Docker Hub push permission, protected environment, owner VEX approval and approved release inputs remain external gates. |
| OMO-008 | P1 / trainer implementation ready; execution blocked | Implement the isolated Transformers/TRL SFT/export/quantization runner for `omo-routing-proposal-v1`; compare full and adapter outputs, evaluate protected held-out gates, and publish lineage plus rollback manifests only after evidence passes. | OMO-012, dry-run preparation and lineage contracts are complete. A larger OMO-013 corpus is required before a meaningful run; artifact signing and any paid operation still require owner approval. |
| OMO-009 | P1 / offline evaluation ready; live evidence blocked | Add fixed-provider outcome ingestion, selective risk/coverage calibration, source/license audit records and a human-review protocol for the enlarged corpus. | Offline schemas can proceed. Live-provider baselines, paid calls and actual human review still require approval. |
| OMO-010 | P2 / blocked deployment | Move caller budget accounting to a managed durable multi-instance store, add measured cost reconciliation and enforce DNS/IP egress through deployment network policy before multi-tenant production use. | Optional SQLite persistence now survives local process restarts; shared-store correctness, provider cost reconciliation and deployment-level DNS/IP enforcement remain. |
| OMO-011 | P2 / blocked deployment integration | Add an owner-controlled registry source and authenticated deployment refresh integration; add provider-specific tokenizer adapters only when independently verified. | Local registry status, freshness threshold, last-known-good reload and the declared tokenizer strategy are complete. Request-time discovery and downloads remain disabled. |
| OMO-013 | P0 / data expansion ready; Hub publication blocked | Expand licensed, human-reviewed prompt families using the implemented deterministic builder; preserve family-level train/development/calibration/protected-test isolation; produce dataset cards and immutable revision manifests. Never emit protected-test records to a training artifact. | OMO-012 and the local build/validation pipeline are complete. The current 30-record source yields only four training records. Hub upload still depends on OMO-006. |
| OMO-014 | P1 / partial (preflight complete; activation blocked) | The manual-only protected GitHub Actions preflight now requires exact code, dataset and base-model revisions; explicit method/hardware/timeout/max-cost/backend/resume inputs; concurrency cancellation; locked dependencies; and dry-run mode. It stops before HF Job execution, checkpoint publication or promotion. | Repository-owned preflight is complete. Activation still depends on OMO-006, OMO-008 and OMO-013 plus owner-approved spend, HF Jobs eligibility, a protected `training` environment, Trackio/checkpoint authority and narrowly scoped credentials. |
| OMO-015 | P1 / pending publication pipeline | Persist every successful training candidate to `BassemZohdy/open-model-orchestrator` with safetensors, tokenizer/template, training configuration, base and dataset revisions, metrics, model card, license provenance and rollback metadata. Use repo-scoped HF Trusted Publisher/OIDC for GitHub-side publication where supported; use a separately scoped short-lived/job secret only where the remote job must push. Publish immutable candidate revisions first and promote no mutable alias until protected evaluation, security and human-review gates pass. | Depends on OMO-003, OMO-004, OMO-006, OMO-008, OMO-009 and OMO-014. Runtime credentials must never receive training or publishing authority. |
| OMO-016 | P0 / pending runtime integration | Add an explicit model-promotion manifest that pins the approved OMO-trained Hub repository, immutable revision, filename, format/quantization, template, size and SHA-256. Download only during a trusted build/preparation step, verify before loading, bundle one approved artifact in the runtime image, and keep request-time Hub access disabled. Re-run the entire local/routing evaluation because a fine-tuned revision inherits no eligibility from the upstream checkpoint. | Depends on OMO-015 and passed protected evaluation. Preserve the preceding upstream manifest as the rollback target. |
| OMO-017 | P0 / pending delivery integration | Extend the Docker release workflow so an approved application commit and OMO model-promotion manifest produce native AMD64/ARM64 candidates for `bzohdy/open-model-orchestrator`; test each published digest offline, assemble one multi-platform manifest, attach SBOM/provenance/signatures and promote immutable version tags before `latest`. Record the exact GitHub commit, HF model revision/checksum and Docker digests in one release manifest. | Depends on OMO-007 and OMO-016. Build/push must occur in protected GitHub Actions; Docker Hub automated builds and model downloads at container startup remain prohibited. |
| OMO-018 | P2 / pending operations | Add model/image lifecycle operations: evidence retention, training-job ID and cost capture, candidate comparison, manual approval/audit trail, rollback drill, tag-retention policy and drift/retraining criteria. Retraining remains an explicit owner action against a new immutable dataset revision; application releases and Hub webhooks must not trigger it automatically. | Depends on the first completed OMO-014 through OMO-017 cycle and measured production-like evidence. |

## External unblocking checklist

These gates cannot be satisfied by repository code and must remain explicit:

| Gate | Owner-controlled action | Tasks unblocked |
|---|---|---|
| HF resources | Create the model and dataset repositories named in OMO-006, verify licenses/visibility, then configure repository-scoped Trusted Publisher claims for the exact GitHub repository, branch and publishing workflow. | OMO-006, OMO-013, OMO-015 |
| Training budget | Enable eligible Hugging Face Jobs billing/credits and approve a maximum hardware flavor, duration and dollar cost for one candidate run. | OMO-008 execution, OMO-014 activation |
| GitHub environments | Configure protected `training` and `release` environments with required reviewers and main-branch restrictions. | OMO-007, OMO-014, OMO-017 |
| Docker Hub publication | Confirm the automation credential can push to `bzohdy/open-model-orchestrator`; login success alone is insufficient. | OMO-007, OMO-017 |
| Security/signing | Approve or reject the scoped DiskCache VEX after review, select the signing authority and obtain an independent sandbox/native-parser review. | OMO-002, OMO-007 |
