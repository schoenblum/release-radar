"""A stand-in for Google's token endpoint and the Analytics Data API, for the end-to-end tests.

Any assertion gets a token. A report for a page whose path holds ``e2e-views-<n>`` counts n
views, a path with ``e2e-nodata`` has no rows, and the one-day report of Test connection counts
1234 views. Nothing here checks a signature: the unit tests do that.
"""

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VIEWS = re.compile(r"e2e-views-(\d+)")


class Google(BaseHTTPRequestHandler):
    def _answer(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802 (the standard library's name)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        if self.path == "/token":
            self._answer(200, {"access_token": "e2e-token", "expires_in": 3599})
            return
        if not self.path.endswith(":runReport"):
            self._answer(404, {"error": {"status": "NOT_FOUND", "message": "no such route"}})
            return
        body = json.loads(raw)
        if "dimensions" not in body:
            self._answer(200, {"rows": [{"metricValues": [{"value": "1234"}]}]})
            return
        expressions = body["dimensionFilter"]["andGroup"]["expressions"]
        host = expressions[0]["filter"]["stringFilter"]["value"]
        paths = expressions[1]["filter"]["inListFilter"]["values"]
        rows = []
        for path in paths:
            found = VIEWS.search(path)
            # One row only, for the variant with the trailing slash, as Google would record it.
            if found and path.endswith("/"):
                rows.append(
                    {
                        "dimensionValues": [{"value": host}, {"value": path}],
                        "metricValues": [{"value": found.group(1)}],
                    }
                )
        self._answer(200, {"rows": rows} if rows else {"rowCount": 0})

    def log_message(self, *args: object) -> None:
        return


# Inside its own container, reached only by the app over the stack's network.
ThreadingHTTPServer(("0.0.0.0", 8081), Google).serve_forever()  # noqa: S104
