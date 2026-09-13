"""Trusted launcher: tighten OS process bounds before replacing it with Monty.

This is not the guest interpreter. Monty's VM supplies guest isolation.
"""

import os
import resource
import sys
from pathlib import Path


def main() -> None:
    binary = Path(sys.executable).parent / "monty"
    limit = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
    os.closerange(3, min(int(limit), 1_048_576))
    # Native fault diagnostics must not become prompt/guest-content logs.
    fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(fd, 2)
    if fd > 2:
        os.close(fd)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
    os.execve(str(binary), [str(binary), *sys.argv[1:]], {"LANG": "C.UTF-8"})
