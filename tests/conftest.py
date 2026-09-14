import json
import sys
from pathlib import Path

import httpx
import pytest

from omo.config import Settings
from omo.contracts import ChatRequest
from omo.provider import OpenAIProvider
from omo.registry import ModelEntry, Registry, RegistryStore
from omo.sandbox import MontySandbox
from omo.service import Orchestrator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FakeModel:
    ready = True
    revision = "fake-test-only"

    def __init__(self, proposal=None):
        self.proposal = proposal or {"action": "external_model", "capability": "text"}
        self.calls = []
        self.token_count = 128

    async def count(self, messages, reserve):
        self.calls.append(messages)
        return self.token_count

    async def generate(self, messages, max_tokens, schema=None):
        self.calls.append(messages)
        return {"text": json.dumps(self.proposal), "finish_reason": "stop", "usage": None}


@pytest.fixture
def entry():
    return ModelEntry(
        id="configured",
        upstream_model="test-model",
        base_url="https://provider.example/v1",
        key_env="OMO_PROVIDER_KEY_TEST",
        enabled=True,
        available=True,
        capabilities=("text", "coding"),
        context_tokens=8192,
        max_output_tokens=256,
        input_usd_per_million=1.0,
        output_usd_per_million=2.0,
        retention="none",
    )


@pytest.fixture
def request_factory():
    def make(text="Write a Java service", **options):
        return ChatRequest.model_validate(
            {
                "messages": [{"role": "user", "content": text}],
                "omo": {"max_cost_usd": 0.01, **options},
            }
        )

    return make


@pytest.fixture
async def sandbox():
    async with MontySandbox(enabled=True) as box:
        yield box


@pytest.fixture
async def service(entry, monkeypatch):
    monkeypatch.setenv("OMO_PROVIDER_KEY_TEST", "test-secret")

    def respond(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "provider answer"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            },
        )

    provider = OpenAIProvider(httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    async with MontySandbox(True) as box:
        yield Orchestrator(
            Settings(external_enabled=True, sandbox_enabled=True),
            FakeModel(),
            RegistryStore(Registry(version="test-1", models=(entry,))),
            box,
            provider,
        )
    await provider.close()
