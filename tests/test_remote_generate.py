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
    def test_require_complete_pain_analysis_rejects_legacy_format(self) -> None:
        with self.assertRaisesRegex(SystemExit, "痛点分析必须是对象"):
            remote_generate.require_complete_pain_analysis({"痛点分析": "1. 旧格式"})

    def test_require_complete_pain_analysis_rejects_empty_item_content(self) -> None:
        data = {
            "痛点分析": {
                "总体概述": "总体说明",
                "痛点列表": [
                    {"名称": f"痛点{i}", "内容": "正文" if i != 6 else " "}
                    for i in range(1, 7)
                ],
            }
        }

        with self.assertRaisesRegex(SystemExit, "第 6 项的内容不能为空"):
            remote_generate.require_complete_pain_analysis(data)
    def test_require_complete_maturity_analysis_rejects_missing_benchmark(self) -> None:
        with self.assertRaisesRegex(SystemExit, "智能工厂对标分析必须是非空对象"):
            remote_generate.require_complete_maturity_analysis({"成熟度评分表已上传": True})

    def test_require_complete_maturity_analysis_accepts_benchmark_score(self) -> None:
        remote_generate.require_complete_maturity_analysis(
            {
                "成熟度评分表已上传": True,
                "智能工厂对标分析": {"成熟度总分": 1.60},
            }
        )
    def test_require_complete_plan_rejects_project_financial_placeholders(self) -> None:
        data = {
            "智改数转建设方案": {
                "总体方案架构": [{"层级": "基础层", "概述": "建设基础设施。"}],
                "建设内容描述": [{"名称": "基础层", "建设内容": "完善工控网络。"}],
                "具体改造项目": [
                    {
                        "项目名称": "设备采集",
                        "预计投入": "待补充",
                        "投资回报周期": "待评估",
                    }
                ],
            }
        }

        with self.assertRaisesRegex(SystemExit, "预计投入必须填写包含金额单位的数值或区间"):
            remote_generate.require_complete_plan(data)

    def test_require_complete_plan_accepts_numeric_estimates(self) -> None:
        remote_generate.require_complete_plan(
            {
                "智改数转建设方案": {
                    "总体方案架构": [{"层级": "基础层", "概述": "建设基础设施。"}],
                    "建设内容描述": [{"名称": "基础层", "建设内容": "完善工控网络。"}],
                    "具体改造项目": [
                        {
                            "项目名称": "设备采集",
                            "预计投入": "60-80万元（估算）",
                            "投资回报周期": "18-24个月（估算）",
                        }
                    ],
                }
            }
        )


if __name__ == "__main__":
    unittest.main()
