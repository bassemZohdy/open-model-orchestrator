"""Run inside the actual image: no external credentials, network disabled by caller."""

import asyncio
import json
import os
import secrets
import subprocess
import time
import urllib.error
import urllib.request


def main():
    environment = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("HF_", "GITHUB_", "OMO_PROVIDER_KEY_", "DOCKER_"))
    }
    environment.update(
        OMO_HOST="127.0.0.1", OMO_SANDBOX_ENABLED="true", OMO_EXTERNAL_ENABLED="false"
    )
    api_key = secrets.token_urlsafe(32)
    environment["OMO_API_KEY"] = api_key
    process = subprocess.Popen(
        ["omo"], env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )

    def request(path, payload=None, headers=None):
        data = None if payload is None else json.dumps(payload).encode()
        r = urllib.request.Request(
            "http://127.0.0.1:8000" + path,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + api_key,
                **(headers or {}),
            },
        )
        with urllib.request.urlopen(r, timeout=20) as response:
            return json.load(response)

    try:
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError("server exited before readiness")
            try:
                if request("/health/ready")["status"] == "ready":
                    break
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(0.1)
        else:
            raise AssertionError("readiness deadline")
        for path in ["/v1/models", "/metrics"]:
            try:
                request(path, headers={"Authorization": "Bearer invalid"})
            except urllib.error.HTTPError as error:
                assert error.code == 401
            else:
                raise AssertionError("protected endpoint accepted an invalid key")
        assert request("/v1/models")["data"][0]["id"] == "omo"
        try:
            request(
                "/v1/chat/completions", {"messages": [{"role": "user", "content": "x" * 40000}]}
            )
        except urllib.error.HTTPError as error:
            assert error.code == 413
        else:
            raise AssertionError("request byte budget not enforced")
        examples = [
            ({"messages": [{"role": "user", "content": "What is gravity?"}]}, "embedded_model"),
            ({"messages": [{"role": "user", "content": "calc 0.1 + 0.2"}]}, "trusted_helper"),
            (
                {
                    "messages": [{"role": "user", "content": "Square the even numbers"}],
                    "omo": {
                        "action": "helper",
                        "helper": {"id": "even_squares", "values": [1, 2, 3, 4]},
                    },
                },
                "monty",
            ),
        ]
        for body, executor in examples:
            r = request("/v1/chat/completions", body)
            assert r["omo"]["executor"] == executor and r["omo"]["status"] == "success", r
            print(
                json.dumps(
                    {
                        "executor": executor,
                        "content": r["choices"][0]["message"]["content"],
                        "usage": r["usage"],
                        "omo": r["omo"],
                    }
                )
            )
    finally:
        process.terminate()
        try:
            process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise AssertionError("graceful shutdown timed out") from None
    diagnostics = process.stderr.read().decode()
    assert "Application shutdown complete" in diagnostics, "lifespan shutdown did not complete"
    # Uvicorn re-raises the captured SIGTERM after clean lifespan shutdown.
    assert process.returncode in (0, -15), process.returncode

    async def isolation_checks():
        from omo.sandbox import MontySandbox

        async with MontySandbox(True) as sandbox:
            for code in [
                "open('/etc/passwd').read()",
                "import socket; socket.socket()",
                "import os; os.getenv('OMO_API_KEY')",
                "import subprocess",
            ]:
                assert (await sandbox.execute(code, {})).status != "success"
            assert (await sandbox.execute("while True:\n pass", {})).status == "timeout"
            assert (await sandbox.execute("[0] * 100000000", {})).status == "resource-limit"
            assert (await sandbox.execute("value = 7\nvalue", {})).value == 7
            assert (await sandbox.execute("value", {})).status == "policy-denied"

    asyncio.run(isolation_checks())
    print("Runtime smoke, authentication, limits, isolation and graceful shutdown passed")


if __name__ == "__main__":
    main()
