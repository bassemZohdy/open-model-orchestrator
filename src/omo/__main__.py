import argparse

import uvicorn

from omo.api import create_app
from omo.config import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="omo")
    parser.add_argument("--config")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    settings = load_settings(
        args.config,
        {k: v for k, v in {"host": args.host, "port": args.port}.items() if v is not None},
    )
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        workers=1,
        access_log=False,
        timeout_graceful_shutdown=5,
        limit_concurrency=64,
        proxy_headers=False,
        server_header=False,
    )


if __name__ == "__main__":
    main()
