"""Tests for handle-check.

All network traffic goes to a local in-process http.server with canned
responses — the suite never depends on the live internet. The checkers'
injectable ``endpoints`` mapping points every service at the local server,
using a path prefix per service so canned 200/404/500 responses can be
served per service.
"""

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from handle_check import checkers
from handle_check.cli import main


class _CannedHandler(BaseHTTPRequestHandler):
    """Serve canned responses from the class-level ROUTES dict.

    ROUTES maps a URL path prefix to (status, body). A request matches the
    first prefix it starts with; anything unmatched is a 404.
    """

    ROUTES = {}
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # keep test output clean
        pass

    def do_GET(self):
        for prefix, (status, body) in self.ROUTES.items():
            if self.path.startswith(prefix):
                data = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()


class LocalServerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _CannedHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def endpoints(self):
        base = f"http://127.0.0.1:{self.port}"
        return {
            "github": base + "/github/users/{name}",
            "npm": base + "/npm/{name}",
            "pypi": base + "/pypi/{name}/json",
            "dockerhub": base + "/dockerhub/{name}/",
            "gitlab": base + "/gitlab/users?username={name}",
        }


class TestCheckers(LocalServerTestCase):
    """free/taken/unknown mapping for each of the 5 services."""

    def _check(self, service, routes):
        _CannedHandler.ROUTES = routes
        return checkers.CHECKERS[service]("somehandle", endpoints=self.endpoints())

    def test_github_free_on_404(self):
        r = self._check("github", {"/github/": (404, '{"message":"Not Found"}')})
        self.assertEqual(r["status"], "available")

    def test_github_taken_on_200(self):
        r = self._check("github", {"/github/": (200, '{"login":"somehandle"}')})
        self.assertEqual(r["status"], "taken")

    def test_github_unknown_on_500(self):
        r = self._check("github", {"/github/": (500, "boom")})
        self.assertEqual(r["status"], "unknown")

    def test_npm_free_on_404(self):
        r = self._check("npm", {"/npm/": (404, '{"error":"Not found"}')})
        self.assertEqual(r["status"], "available")

    def test_npm_taken_on_200(self):
        r = self._check("npm", {"/npm/": (200, '{"name":"somehandle"}')})
        self.assertEqual(r["status"], "taken")

    def test_npm_unknown_on_403(self):
        r = self._check("npm", {"/npm/": (403, "forbidden")})
        self.assertEqual(r["status"], "unknown")

    def test_pypi_free_on_404(self):
        r = self._check("pypi", {"/pypi/": (404, '{"message":"Not Found"}')})
        self.assertEqual(r["status"], "available")

    def test_pypi_taken_on_200(self):
        r = self._check("pypi", {"/pypi/": (200, '{"info":{"name":"somehandle"}}')})
        self.assertEqual(r["status"], "taken")

    def test_pypi_unknown_on_500(self):
        r = self._check("pypi", {"/pypi/": (500, "boom")})
        self.assertEqual(r["status"], "unknown")

    def test_dockerhub_free_on_404(self):
        r = self._check("dockerhub", {"/dockerhub/": (404, '{"detail":"Not found"}')})
        self.assertEqual(r["status"], "available")

    def test_dockerhub_taken_on_200(self):
        r = self._check("dockerhub", {"/dockerhub/": (200, '{"name":"somehandle"}')})
        self.assertEqual(r["status"], "taken")

    def test_dockerhub_unknown_on_429(self):
        r = self._check("dockerhub", {"/dockerhub/": (429, "slow down")})
        self.assertEqual(r["status"], "unknown")

    def test_gitlab_free_on_empty_list(self):
        r = self._check("gitlab", {"/gitlab/": (200, "[]")})
        self.assertEqual(r["status"], "available")

    def test_gitlab_taken_on_nonempty_list(self):
        r = self._check("gitlab", {"/gitlab/": (200, '[{"username":"somehandle"}]')})
        self.assertEqual(r["status"], "taken")

    def test_gitlab_unknown_on_500(self):
        r = self._check("gitlab", {"/gitlab/": (500, "boom")})
        self.assertEqual(r["status"], "unknown")

    def test_gitlab_unknown_on_bad_json(self):
        r = self._check("gitlab", {"/gitlab/": (200, "not-json")})
        self.assertEqual(r["status"], "unknown")


class TestCheckAll(LocalServerTestCase):
    def test_all_services_mixed(self):
        _CannedHandler.ROUTES = {
            "/github/": (404, ""),
            "/npm/": (200, "{}"),
            "/pypi/": (500, ""),
            "/dockerhub/": (404, ""),
            "/gitlab/": (200, "[]"),
        }
        results = checkers.check_all("somehandle", endpoints=self.endpoints())
        by_service = {r["service"]: r["status"] for r in results}
        self.assertEqual(by_service, {
            "github": "available",
            "npm": "taken",
            "pypi": "unknown",
            "dockerhub": "available",
            "gitlab": "available",
        })

    def test_unknown_on_unreachable_server(self):
        dead = {s: "http://127.0.0.1:1/x/{name}" for s in checkers.SERVICES}
        results = checkers.check_all("somehandle", endpoints=dead)
        self.assertTrue(all(r["status"] == "unknown" for r in results))


class TestCLI(unittest.TestCase):
    def test_usage_error_no_name(self):
        self.assertEqual(main([]), 2)

    def test_usage_error_json_flag_only(self):
        self.assertEqual(main(["--json"]), 2)


class TestCLIJsonShape(LocalServerTestCase):
    def test_json_output_shape(self):
        _CannedHandler.ROUTES = {
            "/github/": (404, ""),
            "/npm/": (200, "{}"),
            "/pypi/": (404, ""),
            "/dockerhub/": (404, ""),
            "/gitlab/": (200, "[]"),
        }
        import handle_check.cli as cli_mod

        orig = cli_mod.check_all
        cli_mod.check_all = lambda name: orig(name, endpoints=self.endpoints())
        try:
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = cli_mod.main(["somehandle", "--json"])
            payload = json.loads(buf.getvalue())
        finally:
            cli_mod.check_all = orig

        self.assertEqual(code, 0)  # no unknowns
        self.assertEqual(payload["name"], "somehandle")
        self.assertEqual(len(payload["results"]), 5)
        self.assertEqual(
            {r["service"] for r in payload["results"]},
            {"github", "npm", "pypi", "dockerhub", "gitlab"},
        )
        for r in payload["results"]:
            self.assertIn(r["status"], ("available", "taken", "unknown"))
            self.assertIn("detail", r)

    def test_exit_code_1_when_unknown(self):
        _CannedHandler.ROUTES = {
            "/github/": (500, ""),
            "/npm/": (200, "{}"),
            "/pypi/": (404, ""),
            "/dockerhub/": (404, ""),
            "/gitlab/": (200, "[]"),
        }
        import handle_check.cli as cli_mod

        orig = cli_mod.check_all
        cli_mod.check_all = lambda name: orig(name, endpoints=self.endpoints())
        try:
            import io
            from contextlib import redirect_stdout

            with redirect_stdout(io.StringIO()):
                code = cli_mod.main(["somehandle"])
        finally:
            cli_mod.check_all = orig
        self.assertEqual(code, 1)

    def test_exit_code_0_when_all_answered(self):
        _CannedHandler.ROUTES = {
            "/github/": (200, "{}"),
            "/npm/": (200, "{}"),
            "/pypi/": (404, ""),
            "/dockerhub/": (404, ""),
            "/gitlab/": (200, "[]"),
        }
        import handle_check.cli as cli_mod

        orig = cli_mod.check_all
        cli_mod.check_all = lambda name: orig(name, endpoints=self.endpoints())
        try:
            import io
            from contextlib import redirect_stdout

            with redirect_stdout(io.StringIO()):
                code = cli_mod.main(["somehandle"])
        finally:
            cli_mod.check_all = orig
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
