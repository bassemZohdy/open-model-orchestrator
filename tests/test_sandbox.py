import asyncio
import os
import signal
import time
from pathlib import Path

import psutil
import pytest

from omo.sandbox import MontySandbox


@pytest.mark.parametrize(
    "code",
    [
        "open('/etc/passwd').read()",
        "open('/proc/self/environ').read()",
        "import os; os.getenv('OMO_CANARY_SECRET')",
        "import socket; socket.socket()",
        "import socket; socket.gethostbyname('example.com')",
        "import subprocess; subprocess.run(['id'])",
        "import ctypes; ctypes.CDLL(None)",
        "import importlib; importlib.import_module('os')",
        "__import__('os').system('id')",
        "eval('1+1')",
        "exec('x=1')",
        "import pip; pip.main(['install','x'])",
        "import multiprocessing",
    ],
)
async def test_real_guest_denies_capabilities(sandbox, code, monkeypatch):
    monkeypatch.setenv("OMO_CANARY_SECRET", "super-secret-canary")
    result = await sandbox.execute(code, {})
    assert result.status != "success"
    assert "super-secret-canary" not in str(result)


async def test_canary_file_not_readable(sandbox, tmp_path):
    path = tmp_path / "canary"
    path.write_text("file-secret-canary")
    result = await sandbox.execute(f"open({str(path)!r}).read()", {})
    assert result.status == "policy-denied"
    assert "file-secret-canary" not in str(result)


async def test_fresh_state(sandbox):
    assert (await sandbox.execute("private_value = 42\nprivate_value", {})).value == 42
    assert (await sandbox.execute("private_value", {})).status == "policy-denied"
    assert (
        await sandbox.execute("[x*x for x in values if x%2 == 0]", {"values": [1, 2, 3, 4]})
    ).value == [4, 16]


@pytest.mark.parametrize(
    "code,expected",
    [
        ("while True:\n pass", "timeout"),
        ("[0] * 100000000", "resource-limit"),
        ('"x" * 20000', "resource-limit"),
        ("def f():\n return f()\nf()", "resource-limit"),
        ("this is not Python!", "unsupported"),
        ("1/0", "execution-error"),
        ('print("x" * 20000)', "resource-limit"),
    ],
)
async def test_actual_limits(sandbox, code, expected):
    start = time.monotonic()
    result = await sandbox.execute(code, {})
    assert result.status == expected
    assert time.monotonic() - start < 2
    assert (await sandbox.execute("6*7", {})).value == 42


async def test_limits_not_request_controlled(sandbox):
    assert (await sandbox.execute("1", {"data": "x" * 9000})).status == "resource-limit"
    assert (await sandbox.execute(" " * 5000, {})).status == "resource-limit"
    assert (await sandbox.execute("1", {"data": object()})).status == "unsupported"


async def test_feature_flag_fails_closed():
    async with MontySandbox(False) as box:
        assert (await box.execute("1+1", {})).status == "policy-denied"


async def get_worker():
    for _ in range(100):
        children = [
            p
            for p in psutil.Process(int(os.readlink("/proc/self"))).children(recursive=True)
            if p.name() == "monty"
        ]
        if children:
            return children[0]
        await asyncio.sleep(0.002)
    raise AssertionError("real Monty worker never appeared")


async def test_worker_crash_is_contained(sandbox):
    task = asyncio.create_task(sandbox.execute("while True:\n pass", {}))
    worker = await get_worker()
    namespace_pid = int(
        next(
            line
            for line in Path(f"/proc/{worker.pid}/status").read_text().splitlines()
            if line.startswith("NSpid:")
        ).split()[-1]
    )
    os.kill(namespace_pid, signal.SIGKILL)
    assert (await task).status == "internal-error"
    assert (await sandbox.execute("21*2", {})).value == 42


async def test_cancellation_reaps_worker(sandbox):
    task = asyncio.create_task(sandbox.execute("while True:\n pass", {}))
    worker = await get_worker()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    for _ in range(100):
        if not worker.is_running() or worker.status() == psutil.STATUS_ZOMBIE:
            break
        await asyncio.sleep(0.01)
    assert not worker.is_running() or worker.status() == psutil.STATUS_ZOMBIE
    assert (await sandbox.execute("40+2", {})).value == 42


async def test_worker_has_no_secrets_or_inherited_files(sandbox, monkeypatch, tmp_path):
    monkeypatch.setenv("OMO_PROVIDER_KEY_TEST", "secret-must-not-inherit")
    path = tmp_path / "inherited-canary"
    with path.open("w+") as file:
        os.set_inheritable(file.fileno(), True)
        task = asyncio.create_task(sandbox.execute("while True:\n pass", {}))
        worker = await get_worker()
        assert "OMO_PROVIDER_KEY_TEST" not in worker.environ()
        assert str(path) not in [f.path for f in worker.open_files()]
        assert (await task).status == "timeout"
