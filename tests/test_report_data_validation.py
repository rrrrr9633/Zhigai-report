import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "zhigai-report-server" / "server" / "app.py"
SPEC = importlib.util.spec_from_file_location("report_server", MODULE_PATH)
report_server = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(report_server)


def valid_pain_analysis() -> dict:
    return {
        "总体概述": "总体问题说明。",
        "痛点列表": [
            {"名称": f"痛点{i}", "内容": f"痛点{i}正文。"}
            for i in range(1, 7)
        ],
    }


class ReportDataValidationTests(unittest.TestCase):
    def test_accepts_six_complete_pain_points(self) -> None:
        report_server.validate_report_data({"痛点分析": valid_pain_analysis()})

    def test_rejects_legacy_string_pain_analysis(self) -> None:
        with self.assertRaisesRegex(report_server.DataValidationError, "必须是对象"):
            report_server.validate_report_data({"痛点分析": "1. 旧格式"})

    def test_rejects_missing_or_empty_pain_fields(self) -> None:
        data = {"痛点分析": valid_pain_analysis()}
        data["痛点分析"]["痛点列表"][4]["内容"] = "  "

        with self.assertRaisesRegex(report_server.DataValidationError, "第 5 项的内容不能为空"):
            report_server.validate_report_data(data)

    def test_rejects_non_six_pain_points(self) -> None:
        data = {"痛点分析": valid_pain_analysis()}
        data["痛点分析"]["痛点列表"].pop()

        with self.assertRaisesRegex(report_server.DataValidationError, "恰好包含 6 项"):
            report_server.validate_report_data(data)


if __name__ == "__main__":
    unittest.main()