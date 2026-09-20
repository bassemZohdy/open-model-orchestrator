# Accounts and release runbook

Verified GitHub account: `bassemZohdy`. Target repository: `bassemZohdy/open-model-orchestrator`, ID 1368293245, public, main branch. Initial checks returned 404; the owner then created the repository. OMO initialized main with a small README and developed on feat/bootstrap-v0.1. No other repository was changed or renamed.

Hugging Face account: `BassemZohdy`. The connector reported read-repos/read-mcp/profile/openid/jobs scopes, with no publishing scope; identity was reverified on 2026-09-13 and the connector reported credential expiry 2026-09-13T18:03:41Z. Revalidate credentials before later operations. The owner created the model target `BassemZohdy/open-model-orchestrator`; it currently has no approved OMO fine-tuned artifact. The dataset target `BassemZohdy/open-model-orchestrator-dataset` and immutable publication authority remain unverified. The deployed base checkpoint is the upstream revision in models/manifest.json; it must not be published as a new OMO fine-tune.

Verified Docker Hub namespace: `bzohdy`; image target `bzohdy/open-model-orchestrator`. Actions login succeeded in run 34754068464/job 103715356976. Authentication is verified; push permission and image publication are not. Account artifact ID 10315684770, SHA-256 `6bfc2ccfbb3413cf9313b9d4dc92a7fa42a7ce948bb08a75af5fbc1edb737b16`.

The owner added Docker Hub Actions variables/secrets. Account preflight accepts `DOCKERHUB_USERNAME` (variable or secret) and `DOCKERHUB_TOKEN` (secret), with `DOCKER_USERNAME`/`DOCKER_TOKEN` aliases. It checks existence and authenticates to Docker Hub without printing the token. An artifact records the namespace and distinguishes authentication from untested push permission. No namespace is guessed from the GitHub username.

## Workflows

- OMO validation: PR/main-push checks, secret scanning, real Monty security contracts, strict typing, dataset/dry-run/release static checks; unpublished bundled container build and offline smoke on native ubuntu-24.04 AMD64 and ubuntu-24.04-arm ARM64. Container vulnerability reports are visible in normal CI; release-mode validation fails on any HIGH/CRITICAL finding.
- Real model validation: trusted repository push/manual/reusable workflow, pinned weights, real model tests and local development evaluation. No paid provider calls.
- Docker Hub account preflight: owner branch push when its workflow changes, or manual dispatch. Only credential existence/login and a non-secret identity artifact.
- Approved application release: manual dispatch on main, explicit exact approved commit and version, strict Python/container vulnerability gates plus real-model validation, release environment, native per-platform build with SBOM/provenance, candidate publication followed by digest-based offline smoke. The observed DiskCache advisory currently blocks candidate publication. No latest/stable alias advances. Stable multi-platform promotion and signature verification remain unimplemented.

Third-party actions are pinned to full commits resolved from upstream version tags. Workflow permissions are read-only except external registry credentials in the publishing job. PR jobs receive no publishing secrets. There are no schedules, paid training jobs, pull_request_target or workflow_run chains. Configure the GitHub `release` environment with required reviewers and narrow branch access before dispatch; code cannot establish those repository settings through the available connector.

## Owner setup and supported commands

```bash
# Execute on an owner's authenticated machine; never paste tokens into chat.
gh secret set DOCKERHUB_TOKEN --repo bassemZohdy/open-model-orchestrator
gh variable set DOCKERHUB_USERNAME --repo bassemZohdy/open-model-orchestrator --body YOUR_VERIFIED_NAMESPACE
# After authorized merge and required gates:
gh workflow run release.yml --repo bassemZohdy/open-model-orchestrator --ref main \
  -f version=0.1.0-rc.1 -f approved_commit=EXACT_MAIN_COMMIT_SHA
```

For HF, use documented trusted publisher configuration for narrowly scoped model/dataset resources where available, or a narrow fine-grained publishing token outside runtime. Verify workflow/ref claims for the actual publishing event; tag-triggered workflows must not copy branch-only claims. Do not grant Jobs or broad account privileges merely to upload a model/dataset.

```bash
hf auth login
hf auth whoami
hf repos create BassemZohdy/open-model-orchestrator-dataset --type dataset
```

These are setup commands, not claims that the resources exist. No HF upload workflow is enabled until the publisher authorization, licensing and artifact identity are verified. Model and application releases must remain separate. Application changes never trigger retraining.

Release manifest must bind exact code commit, platform image digests, model checksum/revision/template/quantization, dataset hash, evaluation and policy/calibration revisions. Candidate records capture partial publication. Stable promotion/signature verification is not yet implemented; keep the previous complete pinned deployment until it is. Never report a skipped workflow as published. Rollback is redeploying the preceding complete approved manifest's image digest, not rebuilding a mutable tag.

An approved model bundle must also pass the offline OMO-015 artifact contract
before publication:

```bash
uv run --no-sync python scripts/check_model_artifact.py \
  --manifest artifacts/model-artifact.json \
  --artifact-root artifacts/model
```

The command verifies the bundle and its evidence only; it does not enable
training, contact a provider, upload to Hugging Face or publish to Docker Hub.
