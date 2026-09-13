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

## Evidence status

Local regression tests verify documentation-only, runtime, dependency,
Docker/model/evaluation, workflow, unknown, multi-commit, rename, deletion,
manual and release-selection contracts. The resulting PR must still be
verified on its actual head with GitHub Actions, including native AMD64/ARM64
container acceptance and the independent Claude review. A local green test
does not claim those remote checks passed.
