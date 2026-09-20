from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Protocol

from omo.config import Settings
from omo.contracts import OmoError


class EmbeddedModel(Protocol):
    revision: str
    ready: bool

    async def generate(
        self, messages: list[dict[str, str]], max_tokens: int, schema: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...
    async def count(self, messages: list[dict[str, str]], reserve: int) -> int: ...


class LlamaModel:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.process: asyncio.subprocess.Process | None = None
        self.lock = asyncio.Lock()
        self.pending = 0
        self.ready = False
        self.revision = "unloaded"
        self.path = str(Path(settings.model_path).resolve())

    def _verify(self) -> None:
        path = Path(self.settings.model_path).resolve(strict=True)
        manifest = json.loads(Path(self.settings.model_manifest).read_text())
        if path.stat().st_size != manifest["size_bytes"]:
            raise ValueError("model size mismatch")
        with path.open("rb") as f:
            if hashlib.file_digest(f, "sha256").hexdigest() != manifest["sha256"]:
                raise ValueError("model checksum mismatch")
        self.revision = manifest["revision"]

    async def start(self) -> None:
        await asyncio.to_thread(self._verify)
        await self._spawn()

    async def _spawn(self) -> None:
        if self.process and self.process.returncode is None:
            return
        self.ready = False
        self.process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            str(Path(__file__).with_name("inference_worker.py")),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env={"LANG": "C.UTF-8"},
            close_fds=True,
            limit=65536,
        )
        if self.process.stdin is None or self.process.stdout is None:
            await self.close()
            raise OmoError("inference_unavailable", 503)
        config = {
            "path": self.path,
            "context": self.settings.context_tokens,
            "threads": self.settings.threads,
        }
        try:
            self.process.stdin.write(json.dumps(config).encode() + b"\n")
            await self.process.stdin.drain()
            async with asyncio.timeout(30):
                line = await self.process.stdout.readline()
            if json.loads(line) != {"ready": True}:
                raise ValueError("model warmup failed")
            self.ready = True
        except BaseException:
            await self.close()
            raise

    async def close(self) -> None:
        self.ready = False
        p, self.process = self.process, None
        if p is not None:
            if p.returncode is None:
                p.kill()
            await p.wait()

    async def _call(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.pending >= self.settings.inference_queue:
            raise OmoError("inference_busy", 429)
        self.pending += 1
        try:
            async with self.lock:
                try:
                    await self._spawn()
                    process = self.process
                    if process is None or process.stdin is None or process.stdout is None:
                        raise OmoError("inference_unavailable", 503)
                    process.stdin.write(json.dumps(payload).encode() + b"\n")
                    await process.stdin.drain()
                    async with asyncio.timeout(self.settings.deadline_seconds):
                        line = await process.stdout.readline()
                    result: dict[str, Any] = json.loads(line)
                    if "error" in result:
                        raise OmoError(result["error"], 422)
                    return result
                except OmoError:
                    raise
                except asyncio.CancelledError:
                    await self.close()
                    raise
                except Exception as exc:
                    await self.close()
                    raise OmoError("inference_unavailable", 503) from exc
        finally:
            self.pending -= 1

    async def generate(
        self, messages: list[dict[str, str]], max_tokens: int, schema: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return await self._call({"messages": messages, "max_tokens": max_tokens, "schema": schema})

    async def count(self, messages: list[dict[str, str]], reserve: int) -> int:
        result = await self._call({"messages": messages, "max_tokens": reserve, "count_only": True})
        return int(result["tokens"])
