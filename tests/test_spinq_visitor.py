import io
import json
import unittest

from scripts.spinq_visitor import VISITOR_LOGIN_URL, create_visitor_session


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class SpinQVisitorTests(unittest.TestCase):
    def test_create_visitor_session_uses_empty_post_and_redacts_token(self):
        observed = {}

        def fake_opener(request, *, timeout):
            observed["url"] = request.full_url
            observed["method"] = request.get_method()
            observed["body"] = request.data
            observed["headers"] = dict(request.header_items())
            observed["timeout"] = timeout
            return FakeResponse(
                json.dumps(
                    {
                        "status": 200,
                        "msg": "",
                        "token": "temporary-token",
                        "name": None,
                        "hasPassword": False,
                    }
                ).encode("utf-8")
            )

        session = create_visitor_session(timeout=3.5, opener=fake_opener)

        self.assertEqual(
            observed,
            {
                "url": VISITOR_LOGIN_URL,
                "method": "POST",
                "body": None,
                "headers": {"Accept": "application/json", "Lang": "en"},
                "timeout": 3.5,
            },
        )
        self.assertEqual(session.token, "temporary-token")
        self.assertEqual(session.auth_headers()["token"], "temporary-token")
        self.assertTrue(session.redacted_summary()["token_present"])
        self.assertNotIn("token", session.redacted_summary())

    def test_create_visitor_session_rejects_failed_response(self):
        def fake_opener(request, *, timeout):
            return FakeResponse(b'{"status": 503, "msg": "unavailable"}')

        with self.assertRaisesRegex(
            RuntimeError, "status=503, msg=unavailable"
        ):
            create_visitor_session(opener=fake_opener)


if __name__ == "__main__":
    unittest.main()
