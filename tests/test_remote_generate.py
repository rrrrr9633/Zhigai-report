import importlib.util
import io
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "remote_generate.py"
SPEC = importlib.util.spec_from_file_location("remote_generate", MODULE_PATH)
remote_generate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(remote_generate)


class ApiBaseUrlResolutionTests(unittest.TestCase):
    def test_resolve_api_base_url_uses_cloud_default_without_overrides(self) -> None:
        self.assertEqual(
            remote_generate.resolve_api_base_url(None, {}),
            "http://154.201.65.69:8787",
        )


class LicensePreflightTests(unittest.TestCase):
    @mock.patch.object(remote_generate, "urlopen")
    def test_request_license_status_sends_bearer_token_to_status_endpoint(self, urlopen: mock.Mock) -> None:
        response = mock.MagicMock()
        response.read.return_value = b'{"ok": true, "status": "active"}'
        urlopen.return_value.__enter__.return_value = response

        status = remote_generate.request_license_status(
            "http://154.201.65.69:8787", "valid-license", 10
        )

        self.assertEqual(status["status"], "active")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://154.201.65.69:8787/license/status")
        self.assertEqual(request.get_header("Authorization"), "Bearer valid-license")

    def test_require_active_license_rejects_non_active_status(self) -> None:
        with self.assertRaisesRegex(SystemExit, "授权已过期"):
            remote_generate.require_active_license({"ok": False, "message": "授权已过期"})

    @mock.patch.object(remote_generate, "urlopen")
    def test_request_license_status_surfaces_missing_license_message(self, urlopen: mock.Mock) -> None:
        urlopen.side_effect = HTTPError(
            "http://example.test/license/status",
            401,
            "Unauthorized",
            {},
            io.BytesIO('{"ok": false, "message": "缺少授权码"}'.encode("utf-8")),
        )

        with self.assertRaisesRegex(RuntimeError, "缺少授权码"):
            remote_generate.request_license_status("http://example.test", "", 10)


if __name__ == "__main__":
    unittest.main()
