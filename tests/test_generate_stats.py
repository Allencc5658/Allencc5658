"""Exercise API failures offline; never consume real tokens or retry delays."""
from contextlib import redirect_stderr
from email.message import Message
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

spec = importlib.util.spec_from_file_location(
    "generate_stats", Path(__file__).resolve().parents[1] / "scripts/generate-stats.py"
)
stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats)


def response(data=None, raw=None, headers=None):
    result = io.BytesIO(json.dumps(data).encode() if raw is None else raw)
    result.headers = headers or {}
    return result


def http_error(code, message="request failed", **headers):
    metadata = Message()
    for key, value in headers.items():
        metadata[key] = str(value)
    return HTTPError(stats.API + "/users/Allencc5658", code, message, metadata,
                     io.BytesIO(json.dumps({"message": message}).encode()))


class PublicAPITests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(stats.os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.sleep = patch.object(stats.time, "sleep").start()
        self.addCleanup(patch.stopall)
        patch.object(stats.time, "time", return_value=1000).start()
        self.log = io.StringIO()
        self.capture = redirect_stderr(self.log)
        self.capture.__enter__()
        self.addCleanup(self.capture.__exit__, None, None, None)

    def api(self, *events, token="test-secret"):
        api = stats.PublicAPI(token=token)
        api.opener = Mock()
        api.opener.open.side_effect = events
        return api

    def test_uses_token_without_logging_it_and_preserves_pagination(self):
        api = self.api(response({"login": "Allencc5658"}, headers={"Link": "next-page"}))
        self.assertEqual(api.get("/users/Allencc5658"), ({"login": "Allencc5658"}, "next-page"))
        request = api.opener.open.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")
        self.assertNotIn("test-secret", self.log.getvalue())

    def test_environment_token_and_local_anonymous_mode(self):
        with patch.dict(stats.os.environ, {"GITHUB_TOKEN": "environment-secret"}):
            self.assertEqual(stats.PublicAPI().token, "environment-secret")
        api = self.api(response({}), token="")
        api.get("/users/Allencc5658")
        self.assertIsNone(api.opener.open.call_args.args[0].get_header("Authorization"))

    def test_actions_requires_explicit_token(self):
        with patch.dict(stats.os.environ, {"GITHUB_ACTIONS": "true"}):
            with self.assertRaisesRegex(RuntimeError, "GITHUB_TOKEN is missing"):
                stats.PublicAPI()

    def test_primary_limit_waits_until_reset_then_recovers(self):
        api = self.api(http_error(403, "API rate limit exceeded", **{
            "x-ratelimit-remaining": "0", "x-ratelimit-reset": "1010",
            "x-github-request-id": "test-request-id",
        }), response({"ok": True}))
        self.assertEqual(api.get("/users/Allencc5658")[0], {"ok": True})
        self.sleep.assert_called_once_with(11)
        self.assertIn("test-request-id", self.log.getvalue())

    def test_secondary_limit_uses_minute_then_exponential_backoff(self):
        api = self.api(http_error(403, "You have exceeded a secondary rate limit"),
                       http_error(403, "You have exceeded a secondary rate limit"), response({}))
        api.get("/users/Allencc5658")
        self.assertEqual([c.args[0] for c in self.sleep.call_args_list], [60, 120])

    def test_rate_limit_headers_take_precedence_over_shorter_retry_after(self):
        api = self.api(http_error(429, **{
            "Retry-After": "3", "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1020"
        }), response({}))
        api.get("/users/Allencc5658")
        self.sleep.assert_called_once_with(21)

    def test_retry_after_on_server_error_and_http_date(self):
        for value, expected in [("15", 15), ("Thu, 01 Jan 1970 00:16:50 GMT", 11)]:
            with self.subTest(value=value):
                self.sleep.reset_mock()
                api = self.api(http_error(503, **{"Retry-After": value}), response({}))
                api.get("/users/Allencc5658")
                self.sleep.assert_called_once_with(expected)

    def test_long_rate_limit_wait_aborts_without_retrying_early(self):
        api = self.api(http_error(429, **{"Retry-After": "3600"}))
        with self.assertRaisesRegex(RuntimeError, "exceeds remaining retry budget"):
            api.get("/users/Allencc5658")
        self.sleep.assert_not_called()
        self.assertEqual(api.opener.open.call_count, 1)

    def test_retry_budget_is_shared_across_endpoints(self):
        api = self.api(http_error(429, **{"Retry-After": "120"}), response({}),
                       http_error(429, **{"Retry-After": "120"}))
        api.get("/users/Allencc5658")
        with self.assertRaisesRegex(RuntimeError, "remaining retry budget 60s"):
            api.get("/users/Allencc5658/repos")
        self.sleep.assert_called_once_with(120)

    def test_permanent_errors_fail_immediately(self):
        for code in (401, 403, 404):
            with self.subTest(code=code):
                api = self.api(http_error(code, "Resource not accessible by integration"))
                with self.assertRaisesRegex(RuntimeError, "not retryable"):
                    api.get("/users/Allencc5658")
                self.assertEqual(api.opener.open.call_count, 1)
        self.sleep.assert_not_called()

    def test_network_and_malformed_response_recover(self):
        for first in (URLError("connection reset"), TimeoutError("timed out"), response(raw=b"{broken")):
            with self.subTest(first=type(first).__name__):
                self.sleep.reset_mock()
                api = self.api(first, response({"ok": True}))
                self.assertEqual(api.get("/users/Allencc5658")[0], {"ok": True})
                self.sleep.assert_called_once_with(2)

    def test_persistent_failure_stops_after_four_attempts(self):
        api = self.api(*[http_error(502) for _ in range(4)])
        with self.assertRaisesRegex(RuntimeError, "retry attempts exhausted"):
            api.get("/users/Allencc5658")
        self.assertEqual(api.opener.open.call_count, 4)
        self.assertEqual([c.args[0] for c in self.sleep.call_args_list], [2, 4, 8])

    def test_error_output_redacts_token(self):
        api = self.api(http_error(403, "bad test-secret\nrequest", **{"X-GitHub-Request-Id": "test-secret"}))
        with self.assertRaises(RuntimeError) as failure:
            api.get("/users/Allencc5658")
        self.assertNotIn("test-secret", str(failure.exception) + self.log.getvalue())
        self.assertIn("[REDACTED]", str(failure.exception))

    def test_redirect_keeps_token_only_on_github_api(self):
        handler = stats.GitHubRedirectHandler()
        req = Request(stats.API + "/old", headers={"Authorization": "Bearer test-secret"})
        redirected = handler.redirect_request(req, None, 301, "moved", {}, stats.API + "/new")
        self.assertEqual(redirected.get_header("Authorization"), "Bearer test-secret")
        for destination in ("https://example.com/new", "http://api.github.com/new"):
            with self.subTest(destination=destination), self.assertRaises(HTTPError):
                handler.redirect_request(req, None, 302, "moved", {}, destination)

    def test_partial_fetch_failure_does_not_replace_existing_images(self):
        user = {"login": "Allencc5658", "followers": 2}
        repo = {"id": 1, "private": False, "owner": {"login": "Allencc5658"},
                "fork": False, "name": "example", "stargazers_count": 1}
        api = self.api(response(user), response([repo]), http_error(403, "Forbidden"))
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for name in ("stats-light.svg", "stats-dark.svg", "languages-light.svg", "languages-dark.svg"):
                (target / name).write_text("previous valid image", encoding="utf-8")
            before = {p.name: p.read_bytes() for p in target.iterdir()}
            with patch.object(stats, "PublicAPI", return_value=api), patch.object(
                stats.sys, "argv", ["generate-stats.py", "--output-dir", directory]
            ), self.assertRaisesRegex(RuntimeError, "not retryable"):
                stats.main()
            self.assertEqual(before, {p.name: p.read_bytes() for p in target.iterdir()})

    def test_authenticated_summary_still_excludes_private_and_foreign_repos(self):
        repo = {"id": 1, "private": False, "owner": {"login": "Allencc5658"},
                "fork": False, "name": "example", "stargazers_count": 1}
        api = Mock()
        api.get.side_effect = [({"login": "Allencc5658", "followers": 2}, ""),
            ([repo, {**repo, "id": 2, "private": True},
              {**repo, "id": 3, "owner": {"login": "someone-else"}}], ""), ({"Python": 100}, "")]
        result = stats.fetch_summary(api)
        self.assertEqual(result["public_repositories"], 1)
        self.assertEqual(result["languages"], {"Python": 100})
        self.assertEqual(api.get.call_count, 3)


if __name__ == "__main__":
    unittest.main()
