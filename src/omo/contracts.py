from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


Action = Literal["local_answer", "helper", "external_model", "clarify", "reject"]
Capability = Literal["text", "coding", "current_information"]


class Message(StrictModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)


class Arithmetic(StrictModel):
    id: Literal["decimal"] = "decimal"
    operation: Literal["add", "subtract", "multiply", "divide"]
    a: str = Field(pattern=r"^-?\d{1,12}(\.\d{1,8})?$")
    b: str = Field(pattern=r"^-?\d{1,12}(\.\d{1,8})?$")
    unit: Literal["", "AED", "USD", "kg", "m", "s"] = ""


class EvenSquares(StrictModel):
    id: Literal["even_squares"] = "even_squares"
    values: list[Annotated[int, Field(ge=-10000, le=10000)]] = Field(max_length=128)


HelperCall = Annotated[Arithmetic | EvenSquares, Field(discriminator="id")]


class Options(StrictModel):
    schema_version: Literal["1"] = "1"
    local_only: bool = False
    action: Literal["auto", "local_answer", "helper", "external_model"] = "auto"
    helper: HelperCall | None = None
    required_capability: Capability = "text"
    max_cost_usd: float = Field(default=0.0, ge=0.0, le=1.0, allow_inf_nan=False)

    @model_validator(mode="after")
    def helper_consistency(self) -> Options:
        if (self.action == "helper") != (self.helper is not None):
            raise ValueError("helper arguments require action=helper")
        return self


class ChatRequest(StrictModel):
    model: Literal["omo"] = "omo"
    messages: list[Message] = Field(min_length=1, max_length=24)
    stream: bool = False
    max_tokens: int = Field(default=96, ge=8, le=256)
    omo: Options = Field(default_factory=Options)

    @model_validator(mode="after")
    def conversation(self) -> ChatRequest:
        if self.messages[-1].role != "user":
            raise ValueError("the final message must be a user message")
        if sum(len(m.content.encode()) for m in self.messages) > 16000:
            raise ValueError("conversation exceeds byte budget; nothing was truncated")
        for i, message in enumerate(self.messages):
            if message.role == "system" and i != 0:
                raise ValueError("system role is only supported at conversation start")
        return self


class Proposal(StrictModel):
    schema_version: Literal["1"] = "1"
    action: Action
    capability: Capability = "text"
    helper: HelperCall | None = None

    @model_validator(mode="after")
    def helper_consistency(self) -> Proposal:
        if (self.action == "helper") != (self.helper is not None):
            raise ValueError("helper arguments require action=helper")
        # No URL, confidence, secret, process, limits or executable fields are accepted.
        return self


class Decision(StrictModel):
    action: Action
    reason: str
    target: str | None = None
    helper: HelperCall | None = None
    policy_version: Literal["omo-policy-1"] = "omo-policy-1"
    registry_version: str = "empty-1"
    confidence: None = None
    calibration: Literal["uncalibrated"] = "uncalibrated"


class Result(StrictModel):
    status: Literal[
        "success",
        "policy-denied",
        "unsupported",
        "timeout",
        "resource-limit",
        "execution-error",
        "internal-error",
    ]
    value: JsonValue = None
    diagnostic: str = ""


class OmoError(Exception):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
