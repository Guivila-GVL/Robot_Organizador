import os
import sys
import argparse
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="Headless Uvicorn Runner for pythonw.exe")
    parser.add_argument("--app", default="app.main:app", help="ASGI app import string")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8002, help="Bind port")
    parser.add_argument("--cwd", default=None, help="Working directory")
    parser.add_argument("--log", default=None, help="Log file path")
    args = parser.parse_args()

    if args.cwd and os.path.exists(args.cwd):
        os.chdir(args.cwd)
        if args.cwd not in sys.path:
            sys.path.insert(0, args.cwd)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(base_dir)
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)

    log_path = args.log or os.path.join(os.getcwd(), f"server_{args.port}.log")
    log_file = open(log_path, "a", encoding="utf-8", buffering=1, errors="replace")
    sys.stdout = log_file
    sys.stderr = log_file

    import logging
    logging.basicConfig(stream=log_file, level=logging.INFO, force=True)

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 Iniciando servidor oculto (pythonw.exe) -> {args.app} en http://{args.host}:{args.port}", flush=True)

    import uvicorn
    uvicorn.run(
        args.app,
        host=args.host,
        port=args.port,
        use_colors=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()

