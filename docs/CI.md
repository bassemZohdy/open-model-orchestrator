# CI selection and validation policy

OMO keeps lightweight validation mandatory and selects the two expensive
suites from the complete change set:

| Event | Base revision | Head revision | Selection |
|---|---|---|---|
| Pull request | PR base SHA | PR head SHA | Change-aware |
| Push, including any branch name | `github.event.before` | pushed SHA | Change-aware; an all-zero initial base runs both |
| Manual dispatch | Not required | Current SHA | Both suites |
| Reusable release call | Not required | Current SHA | Both suites; release also enables strict security |

The change job checks out the exact head used for classification with complete
history. It parses NUL-delimited Git name-status output, including both old and
new names for renames/copies and paths for deletions. Multiple commits are
covered by comparing the event base and head directly.

Only known documentation paths can skip both expensive suites. Runtime source,
dependencies, model/evaluation inputs, Docker/build inputs and relevant CI
workflows select the affected suite. Empty, unknown, malformed or unavailable
change sets fail safe by selecting both suites. This policy intentionally
accepts extra validation when classification is uncertain.

The `checks` and `secrets` jobs in the main CI workflow have no path filter and
remain mandatory. A skipped `native-container` or `real-model` job represents a
deliberate, successful selection decision; the selection job itself is always
run. Release workflows explicitly force both expensive suites and retain all
publication and strict-security gates.

## Security, evaluation and publication contracts

Native Trivy reports are passed through scripts/check_security_report.py.
Normal CI preserves every HIGH/CRITICAL finding, counts findings without a
fixed version, and marks the report for manual review. Strict release mode
fails on any finding; there is no advisory ignore-list or reachability waiver
in the workflow.

evaluation/benchmark_contract.json pins the candidate comparison set and
predeclares policy, protected-quality, incorrect-local-answer, latency and
RSS gates. Unmeasured or license-review-required candidates cannot be treated
as promotion evidence. config/publication.yaml binds the upstream model and
original dataset identities while keeping HF publishing disabled until the
owner grants narrowly scoped authority.

scripts/promote_release.py validates two matching native candidate manifests
and requires passed security, SBOM, provenance and signature evidence before
writing a stable manifest. It does not mutate registry tags; that final
operation remains protected release-environment work.

## Evidence status

Local regression tests verify documentation-only, runtime, dependency,
Docker/model/evaluation, workflow, unknown, multi-commit, rename, deletion,
manual and release-selection contracts. The resulting PR must still be
verified on its actual head with GitHub Actions, including native AMD64/ARM64
container acceptance and the independent Claude review. A local green test
does not claim those remote checks passed.
