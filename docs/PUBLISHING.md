# Publication gates

The repository includes machine-checkable contracts for OMO-006 and OMO-007:

- `config/publication.yaml` binds the exact upstream model revision and the
  original dataset target while keeping publishing disabled.
- `scripts/check_publication_contract.py` rejects model relabeling and identity
  drift without contacting Hugging Face.
- `scripts/promote_release.py` requires matching native AMD64 and ARM64
  candidates plus passed security, SBOM, provenance and signature evidence.

These checks do not create Hugging Face repositories, upload data, sign OCI
images or move registry aliases. Those actions require owner-controlled
publishing/signing credentials and the protected release environment. The
upstream SmolLM2 bytes must remain identified as upstream weights, not an OMO
fine-tune.

Training preparation is separately lineage-bound in
[`config/training.yaml`](../config/training.yaml). It remains dry-run-only and
cannot create a publishable model artifact until the training, export,
quantization, evaluation and signing gates are independently approved.

Before an approved model can enter the promotion boundary,
[`scripts/check_model_artifact.py`](../scripts/check_model_artifact.py) validates
the complete bundle offline. The manifest must bind safetensors weights, the
tokenizer/template, configuration, model card, exact file checksums, code and
dataset lineage, measured held-out evidence, license provenance and the
upstream rollback revision. It never downloads, trains or publishes anything.

The disabled-by-default [`config/model-promotion.yaml`](../config/model-promotion.yaml)
defines the next boundary: an approved fine-tuned revision must be pinned by
Hub repository, immutable revision, filename, format, template, size and
SHA-256. [`scripts/materialize_model.py`](../scripts/materialize_model.py) can
materialize that exact artifact only in a trusted build step and verifies it
before replacement. Runtime request-time downloads are permanently disabled;
the upstream `models/manifest.json` remains the rollback target until a full
evaluation and release approval replace it.
