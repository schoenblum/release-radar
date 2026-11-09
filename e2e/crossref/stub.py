"""A stand-in for Crossref's works endpoint, for the end-to-end tests only.

Any DOI under 10.5555/e2e. is a synthetic paper whose title names the DOI's last part, so a
test can tell its own paper from another's. Every other DOI is unknown (404).
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

PREFIX = "10.5555/e2e."


class Works(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (the standard library's name)
        doi = unquote(self.path.rsplit("/works/", 1)[-1]).lower()
        if not doi.startswith(PREFIX):
            self.send_response(404)
            self.end_headers()
            return
        tag = doi[len(PREFIX) :]
        body = json.dumps(
            {
                "message": {
                    "title": [f"A synthetic paper about {tag}"],
                    "container-title": ["Journal of Synthetic Examples"],
                    "published": {"date-parts": [[2026, 3, 9]]},
                    "author": [
                        {"given": "Test", "family": "Person"},
                        {"name": "Example Consortium"},
                    ],
                }
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        return


# Inside its own container, reached only by the app over the stack's network.
ThreadingHTTPServer(("0.0.0.0", 8080), Works).serve_forever()  # noqa: S104
