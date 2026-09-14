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
