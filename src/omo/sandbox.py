from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Literal, Protocol, Self

from pydantic import JsonValue, TypeAdapter, ValidationError
from pydantic_monty import (
    AsyncMonty,
    MontyCrashedError,
    MontyError,
    MontyRuntimeError,
    MontySyntaxError,
)

from omo.contracts import Result

JSON: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)


class SandboxExecutor(Protocol):
    async def execute(self, code: str, inputs: dict[str, JsonValue]) -> Result: ...


class MontySandbox:
    """Language isolation in Monty; its native pool supplies crash containment.

    No mounts, OS handlers, host objects or guest-callable callbacks. Limits are
    application constants, never model/request arguments. Each worker handles
    one checkout then is recycled, including after resource faults.
    """

    MAX_CODE = 4096
    MAX_INPUT = 8192
    MAX_OUTPUT = 8192

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled
        self.pool = AsyncMonty(
            binary_path=Path(sys.executable).parent / "omo-monty-worker",
            min_processes=0,
            max_processes=2,
            checkout_timeout=0.2,
            request_timeout=1.0,
            max_checkouts_per_worker=1,
        )

    async def __aenter__(self) -> Self:
        if self.enabled:
            await self.pool.__aenter__()
        return self

    async def __aexit__(self, *args: object) -> None:
        if self.enabled:
            await self.pool.__aexit__(*args)

    async def execute(self, code: str, inputs: dict[str, JsonValue]) -> Result:
        if not self.enabled:
            return Result(status="policy-denied", diagnostic="sandbox disabled")
        try:
            # JSON serialization is the only accepted guest input boundary.
            serialized = json.dumps(inputs, allow_nan=False)
            JSON.validate_json(serialized)
        except (ValueError, TypeError, ValidationError):
            return Result(status="unsupported", diagnostic="JSON inputs required")
        if len(code.encode()) > self.MAX_CODE or len(serialized.encode()) > self.MAX_INPUT:
            return Result(status="resource-limit", diagnostic="sandbox input budget")
        printed_bytes = 0

        def discard_print(stream: Literal["stdout", "stderr"], value: str) -> None:
            nonlocal printed_bytes
            printed_bytes += len(value.encode())
            if printed_bytes > self.MAX_OUTPUT:
                raise ValueError("output budget")

        try:
            # Includes checkout, parsing, execution, print callback and IPC.
            async with asyncio.timeout(1.5):
                async with self.pool.checkout(
                    limits={
                        "max_duration_secs": 0.1,
                        "max_memory": 8_000_000,
                        "max_recursion_depth": 32,
                        "max_suspensions": 2,
                    }
                ) as session:
                    output = await session.feed_run(
                        code,
                        inputs=json.loads(serialized),
                        external_lookup={},
                        print_callback=discard_print,
                    )
                    value = JSON.validate_python(output, strict=True)
                    if len(json.dumps(value, allow_nan=False).encode()) > self.MAX_OUTPUT:
                        return Result(status="resource-limit", diagnostic="sandbox output budget")
                    return Result(status="success", value=value)
        except asyncio.CancelledError:
            # Context exits drop the checkout; upstream cancellation kills work.
            raise
        except TimeoutError:
            return Result(status="timeout", diagnostic="sandbox deadline")
        except MontyCrashedError as exc:
            return Result(
                status="timeout" if exc.timed_out else "internal-error",
                diagnostic="sandbox worker unavailable",
            )
        except MontySyntaxError:
            return Result(status="unsupported", diagnostic="unsupported Python subset syntax")
        except MontyRuntimeError as exc:
            # Never return guest diagnostics or embedded source/inputs.
            kind = exc.display(format="type-msg").split(":", 1)[0]
            status: Literal["timeout", "resource-limit", "policy-denied", "execution-error"]
            if kind == "TimeoutError":
                status = "timeout"
            elif kind in {"MemoryError", "RecursionError"} or printed_bytes > self.MAX_OUTPUT:
                status = "resource-limit"
            elif kind in {"PermissionError", "ModuleNotFoundError", "NameError", "RuntimeError"}:
                status = "policy-denied"
            else:
                status = "execution-error"
            return Result(status=status, diagnostic="sandbox execution stopped")
        except (ValueError, TypeError, ValidationError):
            return Result(status="resource-limit", diagnostic="sandbox output invalid or too large")
        except MontyError:
            return Result(status="internal-error", diagnostic="sandbox worker failed")
