from __future__ import annotations

import json
import time
from typing import Any

from pydantic import ValidationError

from omo.access import BudgetLedger, Caller
from omo.classification import ANALYSIS_SCHEMA, analysis_messages
from omo.config import Settings
from omo.contracts import Arithmetic, ChatRequest, Decision, OmoError, Proposal
from omo.helpers import arithmetic
from omo.inference import EmbeddedModel
from omo.policy import LOCAL_REFERENCES, decide, estimated_cost
from omo.provider import OpenAIProvider
from omo.registry import Registry, RegistryStore
from omo.sandbox import SandboxExecutor


class Orchestrator:
    def __init__(
        self,
        settings: Settings,
        model: EmbeddedModel,
        registry: RegistryStore,
        sandbox: SandboxExecutor,
        provider: OpenAIProvider,
        budget_ledger: BudgetLedger | None = None,
    ) -> None:
        self.settings, self.model, self.registry = settings, model, registry
        self.sandbox, self.provider = sandbox, provider
        self.budget_ledger = budget_ledger

    async def route(
        self, request: ChatRequest, snapshot: Registry, caller: Caller | None = None
    ) -> Decision:
        policy_request = request
        allowed_retention = None
        allowed_hosts = None
        if caller is not None:
            policy_request = request.model_copy(
                update={
                    "omo": request.omo.model_copy(
                        update={"max_cost_usd": min(request.omo.max_cost_usd, caller.max_cost_usd)}
                    )
                }
            )
            allowed_retention = caller.allowed_retention
            allowed_hosts = caller.allowed_hosts
        first = decide(
            policy_request,
            snapshot,
            self.settings,
            allowed_retention=allowed_retention,
            allowed_hosts=allowed_hosts,
        )
        if first.reason != "analysis_needed":
            return first
        if policy_request.omo.action == "external_model":
            proposal = Proposal(
                action="external_model", capability=policy_request.omo.required_capability
            )
            return decide(
                policy_request,
                snapshot,
                self.settings,
                proposal,
                allowed_retention=allowed_retention,
                allowed_hosts=allowed_hosts,
            )
        messages = analysis_messages(request.messages)
        try:
            tokens = await self.model.count(messages, 64)
            if tokens > self.settings.analysis_tokens:
                # Full external history is retained. Reject analysis overflow
                # instead of pretending an omitted conversation was analyzed.
                return Decision(
                    action="reject",
                    reason="analysis_context_exceeded",
                    registry_version=snapshot.version + ":" + snapshot.digest,
                )
            output = await self.model.generate(messages, 64, ANALYSIS_SCHEMA)
            proposal = Proposal.model_validate_json(output["text"])
        except (ValidationError, ValueError, TypeError, KeyError):
            return Decision(
                action="reject",
                reason="invalid_model_proposal",
                registry_version=snapshot.version + ":" + snapshot.digest,
            )
        return decide(
            policy_request,
            snapshot,
            self.settings,
            proposal,
            allowed_retention=allowed_retention,
            allowed_hosts=allowed_hosts,
        )

    async def chat(self, request: ChatRequest, caller: Caller | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        snapshot = self.registry.snapshot
        decision = await self.route(request, snapshot, caller)
        routed = time.perf_counter()
        usage = None
        attempts = 0
        estimated = None
        actual_model = "omo"
        executor = "policy"
        status = "success"
        if decision.action == "local_answer":
            if self.model.revision != "593b5a2e04c8f3e4ee880263f93e0bd2901ad47f":
                raise OmoError("model_revision_not_evaluated", 422)
            output = await self.model.generate(
                [
                    {
                        "role": "system",
                        "content": "Answer the question accurately in one short sentence.",
                    },
                    *[m.model_dump() for m in request.messages],
                ],
                min(request.max_tokens, 96),
            )
            text = output["text"]
            references = LOCAL_REFERENCES[request.messages[0].content]
            if (
                not isinstance(text, str)
                or not all(w in text.lower() for w in references)
                or output["finish_reason"] != "stop"
                or len(text) > 800
            ):
                raise OmoError("local_output_failed_validation", 422)
            usage = output["usage"]
            actual_model = "smollm2-360m-instruct-q8_0"
            executor = "embedded_model"
        elif decision.action == "helper":
            call = decision.helper
            assert call is not None
            if isinstance(call, Arithmetic):
                result = arithmetic(call)
                executor = "trusted_helper"
            else:
                result = await self.sandbox.execute(
                    "[x * x for x in values if x % 2 == 0]",
                    {"values": list(call.values)},
                )
                executor = "monty"
                if result.status == "success":
                    # Execution alone is insufficient: independently validate the
                    # transformation contract without asking an LLM to rewrite it.
                    expected = [x * x for x in call.values if x % 2 == 0]
                    if result.value != expected:
                        raise OmoError("sandbox_result_invalid", 500)
            status = result.status
            text = (
                json.dumps(result.value, ensure_ascii=False)
                if status == "success"
                else result.diagnostic
            )
        elif decision.action == "external_model":
            entry = next(m for m in snapshot.models if m.id == decision.target)
            estimated = estimated_cost(entry, request)
            if (
                caller is not None
                and self.budget_ledger is not None
                and estimated is not None
                and not self.budget_ledger.reserve(caller, estimated * 2)
            ):
                raise OmoError("caller_budget_exceeded", 429)
            output = (
                await self.provider.collect_stream(entry, request)
                if request.stream
                else await self.provider.complete(entry, request)
            )
            text, usage, attempts = output["text"], output["usage"], output["attempts"]
            actual_model, executor = entry.id, "external_model"
        elif decision.action == "clarify":
            text = "Please provide the task details, or use the documented typed helper arguments."
            status = "unsupported"
        else:
            text = "This request has no permitted execution path: " + decision.reason + "."
            status = "policy-denied"
        return {
            "model": actual_model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
            "usage": usage,
            "omo": {
                **decision.model_dump(exclude={"helper"}),
                "executor": executor,
                "status": status,
                "model_revision": self.model.revision,
                "provider_attempts": attempts,
                "estimated_call_cost_usd": estimated,
                "routing_ms": round((routed - started) * 1000, 3),
                "total_ms": round((time.perf_counter() - started) * 1000, 3),
            },
        }
