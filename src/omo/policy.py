from __future__ import annotations

from omo.config import Settings
from omo.contracts import ChatRequest, Decision, Proposal
from omo.helpers import fast_helper
from omo.registry import ModelEntry, Registry

# Exact single-turn, English development envelope; no semantic expansion or
# history-dependent local claims. Evaluated with the pinned 360M checkpoint.
LOCAL_REFERENCES: dict[str, tuple[str, ...]] = {
    "What is a noun?": ("person", "place", "thing"),
    "What is gravity?": ("force", "mass"),
    "What is photosynthesis?": ("light", "energy"),
    "What is the opposite of hot?": ("cold",),
}


def local_eligible(request: ChatRequest) -> bool:
    return (
        len(request.messages) == 1
        and request.messages[0].role == "user"
        and request.messages[0].content in LOCAL_REFERENCES
        and request.omo.required_capability == "text"
    )


def estimated_input_upper_bound(request: ChatRequest) -> int:
    # UTF-8 byte count + framing reserve is deliberately conservative. External
    # models must be configured with a tokenizer whose token count is <= bytes
    # plus this overhead; adapters for other encodings remain unsupported.
    return sum(len(m.content.encode()) + 32 for m in request.messages) + 64


def estimated_cost(entry: ModelEntry, request: ChatRequest) -> float | None:
    if entry.input_usd_per_million is None or entry.output_usd_per_million is None:
        return None
    return (
        estimated_input_upper_bound(request) * entry.input_usd_per_million
        + request.max_tokens * entry.output_usd_per_million
    ) / 1_000_000


def eligible_models(
    request: ChatRequest, proposal: Proposal, registry: Registry, settings: Settings
) -> list[ModelEntry]:
    if request.omo.local_only or not settings.external_enabled:
        return []
    required = {"text", request.omo.required_capability, proposal.capability}
    # V0.1 has no browsing/retrieval adapter; never equate a bigger LLM with freshness.
    if "current_information" in required:
        return []
    budget = min(settings.external_max_cost_usd, request.omo.max_cost_usd)
    eligible = []
    for m in registry.models:
        if not m.enabled or not m.available or not required.issubset(m.capabilities):
            continue
        if estimated_input_upper_bound(request) + request.max_tokens > m.context_tokens:
            continue
        if request.max_tokens > m.max_output_tokens:
            continue
        cost = estimated_cost(m, request)
        if cost is None or cost * 2 > budget:
            continue
        eligible.append(m)
    return sorted(eligible, key=lambda m: (m.priority, m.id))


def decide(
    request: ChatRequest, registry: Registry, settings: Settings, proposal: Proposal | None = None
) -> Decision:
    version = registry.version + ":" + registry.digest
    if request.omo.required_capability == "current_information":
        return Decision(action="reject", reason="retrieval_unavailable", registry_version=version)
    if request.omo.action == "helper":
        assert request.omo.helper is not None
        if request.omo.helper.id == "even_squares" and not settings.sandbox_enabled:
            return Decision(action="reject", reason="sandbox_disabled", registry_version=version)
        return Decision(
            action="helper",
            reason="explicit_validated_helper",
            helper=request.omo.helper,
            registry_version=version,
        )
    if request.omo.action in {"auto", "local_answer"}:
        helper = fast_helper(request)
        if helper is not None and request.omo.action == "auto":
            return Decision(
                action="helper",
                reason="exact_calculation_command",
                helper=helper,
                registry_version=version,
            )
        if local_eligible(request):
            return Decision(
                action="local_answer",
                reason="evaluated_development_envelope",
                registry_version=version,
            )
        if request.omo.action == "local_answer":
            return Decision(
                action="reject", reason="outside_local_envelope", registry_version=version
            )
    if proposal is None:
        return Decision(action="clarify", reason="analysis_needed", registry_version=version)
    if proposal.action == "reject":
        return Decision(action="reject", reason="model_rejected", registry_version=version)
    if proposal.action == "clarify":
        return Decision(action="clarify", reason="missing_task_details", registry_version=version)
    if proposal.capability == "current_information":
        return Decision(action="reject", reason="retrieval_unavailable", registry_version=version)
    # Model helper arguments are not authorized in this unevaluated checkpoint.
    # Only explicit typed arguments / exact calc grammar enter helper execution.
    if proposal.action == "helper":
        return Decision(
            action="clarify", reason="explicit_helper_arguments_required", registry_version=version
        )
    eligible = eligible_models(request, proposal, registry, settings)
    if eligible:
        return Decision(
            action="external_model",
            reason="eligible_configured_priority",
            target=eligible[0].id,
            registry_version=version,
        )
    return Decision(action="reject", reason="no_eligible_target", registry_version=version)
