"""Trusted model worker. JSON over pipes, one persistent model, no network use."""

from __future__ import annotations

import json
import sys
from typing import Any, cast

from llama_cpp import Llama
from llama_cpp.llama_grammar import LlamaGrammar


def _parse_request(line: str) -> dict[str, Any] | None:
    if not line or len(line.encode()) > 65536:
        return None
    try:
        request = json.loads(line)
    except (TypeError, ValueError):
        return None
    if not isinstance(request, dict):
        return None
    messages = request.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 24:
        return None
    total_bytes = 0
    for message in messages:
        if (
            not isinstance(message, dict)
            or set(message) != {"role", "content"}
            or message["role"] not in {"system", "user", "assistant"}
            or not isinstance(message["content"], str)
            or not 1 <= len(message["content"]) <= 12000
        ):
            return None
        total_bytes += len(message["content"].encode())
    if total_bytes > 16000:
        return None
    max_tokens = request.get("max_tokens")
    if type(max_tokens) is not int or not 8 <= max_tokens <= 256:
        return None
    if (
        "schema" in request
        and request["schema"] is not None
        and not isinstance(request["schema"], dict)
    ):
        return None
    if "count_only" in request and type(request["count_only"]) is not bool:
        return None
    return request


def main() -> None:
    config = json.loads(sys.stdin.readline(8192))
    model = Llama(
        model_path=config["path"],
        n_ctx=config["context"],
        n_threads=config["threads"],
        n_batch=128,
        n_gpu_layers=0,
        chat_format="chatml",
        seed=42,
        verbose=False,
    )
    # Explicit reviewed template; do not execute arbitrary model metadata templates.
    model.create_chat_completion(
        messages=[{"role": "user", "content": "Hi"}], max_tokens=1, temperature=0
    )
    print(json.dumps({"ready": True}), flush=True)
    for line in sys.stdin:
        try:
            request = _parse_request(line)
            if request is None:
                print(json.dumps({"error": "invalid_request"}), flush=True)
                continue
            messages = request["messages"]
            # Same ChatML tokens as the selected handler, including the default
            # system text when missing. Count through the loaded model tokenizer.
            if not messages or messages[0]["role"] != "system":
                messages = [
                    {"role": "system", "content": "You are a helpful assistant."}
                ] + messages
            prompt = "".join(
                f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n" for m in messages
            )
            prompt += "<|im_start|>assistant\n"
            tokens = len(model.tokenize(prompt.encode(), special=True))
            if tokens + request["max_tokens"] + 16 > config["context"]:
                print(json.dumps({"error": "context_exceeded"}), flush=True)
                continue
            if request.get("count_only"):
                print(json.dumps({"tokens": tokens}), flush=True)
                continue
            grammar = None
            if request.get("schema"):
                grammar = LlamaGrammar.from_json_schema(
                    json.dumps(request["schema"]), verbose=False
                )
            result = cast(
                dict[str, Any],
                model.create_chat_completion(
                    messages=messages,
                    max_tokens=request["max_tokens"],
                    temperature=0,
                    seed=42,
                    grammar=grammar,
                ),
            )
            print(
                json.dumps(
                    {
                        "text": result["choices"][0]["message"]["content"],
                        "finish_reason": result["choices"][0]["finish_reason"],
                        "usage": result["usage"],
                    }
                ),
                flush=True,
            )
        except Exception:
            # No model/user content or parser diagnostics cross into API errors.
            print(json.dumps({"error": "inference_failed"}), flush=True)
    model.close()


if __name__ == "__main__":
    main()
