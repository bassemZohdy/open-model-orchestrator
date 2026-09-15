# OMO routing and classification contract

OMO's model-training objective is a bounded routing proposal, not an
authorization model and not a general local-answer generator. The model emits
only the strict Proposal schema from
[src/omo/contracts.py](../src/omo/contracts.py):

| Model label | Meaning |
|---|---|
| external_model | Propose an eligible external-model response. |
| helper | Propose one allowlisted helper plus its typed arguments. |
| clarify | Ask for missing information before a route can be proposed. |

The model does not emit an executable target, URL, credentials, code, process
limits or confidence. A helper proposal must use the existing discriminated
Arithmetic or EvenSquares schemas. Unknown fields, unknown labels, missing
helper arguments and ambiguous values fail closed.

Deterministic code retains the local_answer and reject outcomes, target
eligibility, provider/account policy, authorization, policy denials, helper
execution and every resource decision. A valid model proposal is only an
input to that policy path; it cannot authorize a request or override a denial.

## Multi-turn serialization

Training and evaluation serialize the complete ordered conversation as a JSON
array of {role, content} objects. Roles are preserved, including a leading
system message, and messages are never silently reordered, truncated or
discarded. The final-user-turn and aggregate byte limits remain enforced by
the existing request contract.

Conversation text is data. Instructions found inside a user or assistant
message cannot change the label contract or gain policy authority. Invalid
examples include malformed JSON, duplicate keys, extra fields, unknown
actions/capabilities, incomplete typed helper arguments, ambiguous references
and conversations without a final user turn.

## Record separation

The existing local-answer examples remain useful for deterministic evaluator
coverage, but they are not classification-training labels. Classification
training records use only external_model, helper or clarify; local_answer and
reject remain separate policy/evaluation records. The offline dataset builder
emits only the train split and writes a deterministic card containing
input/output SHA-256 values. It never copies the protected test split.

This contract does not claim model quality, calibration or a trained OMO
artifact. Those require the blocked evidence, training authority and
publication gates tracked in TODO.md.
