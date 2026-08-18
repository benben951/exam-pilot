import argparse
import mimetypes
import sys
from http.server import ThreadingHTTPServer

import server


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    mimetypes.add_type("text/javascript", ".js")
    httpd = ThreadingHTTPServer((args.host, args.port), server.Handler)
    print(f"ExamPilot local API running at http://{args.host}:{args.port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
