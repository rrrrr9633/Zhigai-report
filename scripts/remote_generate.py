#!/usr/bin/env python3
"""智改数转报告远程生成客户端。

本地只做数据上传和结果保存，不包含报告生成逻辑和 docx 模板。
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
DEFAULT_CONFIG_PATH = Path.home() / ".zhigai-report" / "config.json"
DEFAULT_API_BASE_URL = "http://154.201.65.69:8787"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_config(path: Path) -> dict[str, Any]:
    if path.exists():
        return read_json(path)
    return {}


def save_config(path: Path, api_base_url: str, license_key: str) -> None:
    write_json(path, {"apiBaseUrl": api_base_url.rstrip("/"), "licenseKey": license_key})


def resolve_api_base_url(explicit_value: str | None, config: dict[str, Any]) -> str:
    return explicit_value or config.get("apiBaseUrl") or DEFAULT_API_BASE_URL


def is_uploadable_path(value: str) -> bool:
    if value.startswith("uploaded://"):
        return False

    path = Path(value).expanduser()
    if path.suffix.lower() not in IMAGE_SUFFIXES:
        return False

    try:
        return path.is_file()
    except OSError:
        return False


def collect_uploads(value: Any, files: dict[str, dict[str, str]]) -> Any:
    if isinstance(value, dict):
        return {key: collect_uploads(item, files) for key, item in value.items()}
    if isinstance(value, list):
        return [collect_uploads(item, files) for item in value]
    if isinstance(value, str) and is_uploadable_path(value):
        path = Path(value).expanduser().resolve()
        upload_id = uuid.uuid4().hex
        mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        files[upload_id] = {
            "filename": path.name,
            "mimeType": mime_type,
            "contentBase64": base64.b64encode(path.read_bytes()).decode("ascii"),
        }
        return f"uploaded://{upload_id}"
    return value


def request_generate(api_base_url: str, license_key: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    url = f"{api_base_url.rstrip('/')}/generate"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {license_key}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"服务端拒绝请求：HTTP {error.code} {message}") from error
    except URLError as error:
        raise RuntimeError(f"无法连接远程生成服务：{error.reason}") from error


def request_license_status(api_base_url: str, license_key: str, timeout: int) -> dict[str, Any]:
    url = f"{api_base_url.rstrip('/')}/license/status"
    request = Request(
        url,
        method="GET",
        headers={"Authorization": f"Bearer {license_key}"},
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        try:
            message = json.loads(body).get("message")
        except json.JSONDecodeError:
            message = None
        raise RuntimeError(message or f"授权校验失败：HTTP {error.code}") from error
    except URLError as error:
        raise RuntimeError(f"无法连接远程授权服务：{error.reason}") from error


def require_active_license(status: dict[str, Any]) -> None:
    if status.get("ok") is True and status.get("status") == "active":
        return
    raise SystemExit(status.get("message") or "授权码无效、已过期或不可用。请提供有效授权码。")


def require_complete_pain_analysis(data: dict[str, Any]) -> None:
    pain_analysis = data.get("痛点分析")
    if not isinstance(pain_analysis, dict):
        raise SystemExit("数据校验失败：痛点分析必须是对象，包含总体概述和痛点列表。")

    if not isinstance(pain_analysis.get("总体概述"), str) or not pain_analysis["总体概述"].strip():
        raise SystemExit("数据校验失败：痛点分析.总体概述不能为空。")

    pain_points = pain_analysis.get("痛点列表")
    if not isinstance(pain_points, list) or len(pain_points) != 6:
        raise SystemExit("数据校验失败：痛点分析.痛点列表必须恰好包含 6 项。")

    for index, pain_point in enumerate(pain_points, start=1):
        if not isinstance(pain_point, dict):
            raise SystemExit(f"数据校验失败：痛点分析.痛点列表第 {index} 项必须是对象。")
        for field in ("名称", "内容"):
            value = pain_point.get(field)
            if not isinstance(value, str) or not value.strip():
                raise SystemExit(f"数据校验失败：痛点分析.痛点列表第 {index} 项的{field}不能为空。")


def require_complete_maturity_analysis(data: dict[str, Any]) -> None:
    benchmark = data.get("智能工厂对标分析")
    confirmation_keys = (
        "成熟度评分表已上传",
        "已上传成熟度评分表",
        "用户已上传成熟度评分表",
        "成熟度评分表上传确认",
    )
    scopes = [data]
    if isinstance(benchmark, dict):
        scopes.append(benchmark)

    def is_confirmed(value: Any) -> bool:
        if value is True:
            return True
        return isinstance(value, str) and value.strip().lower() in {
            "true", "yes", "y", "1", "已上传", "用户已上传", "确认已上传"
        }

    confirmed = any(
        is_confirmed(scope.get(key))
        for scope in scopes
        for key in confirmation_keys
    )
    if not confirmed:
        return
    if not isinstance(benchmark, dict) or not benchmark:
        raise SystemExit("数据校验失败：成熟度评分表已上传时，智能工厂对标分析必须是非空对象。")
    score = benchmark.get("成熟度总分")
    if not (
        isinstance(score, (int, float)) and not isinstance(score, bool)
        or isinstance(score, str) and score.strip()
    ):
        raise SystemExit("数据校验失败：成熟度评分表已上传时，智能工厂对标分析.成熟度总分不能为空。")


def require_complete_plan(data: dict[str, Any]) -> None:
    plan = data.get("智改数转建设方案")
    project_scopes: list[tuple[str, Any]] = [("改造项目", data.get("改造项目"))]
    if plan is not None:
        if not isinstance(plan, dict):
            raise SystemExit("数据校验失败：智改数转建设方案必须是对象。")
        for field, content_keys in (
            ("总体方案架构", ("概述", "内容")),
            ("建设内容描述", ("建设内容", "内容")),
        ):
            sections = plan.get(field)
            if not isinstance(sections, list) or not sections:
                raise SystemExit(f"数据校验失败：智改数转建设方案.{field}必须是非空数组。")
            for index, section in enumerate(sections, start=1):
                if not isinstance(section, dict) or not any(
                    isinstance(section.get(key), str) and section[key].strip()
                    for key in content_keys
                ):
                    raise SystemExit(
                        f"数据校验失败：智改数转建设方案.{field}第 {index} 项必须填写"
                        f"{'或'.join(content_keys)}。"
                    )
        project_scopes.append(("智改数转建设方案.具体改造项目", plan.get("具体改造项目")))

    for path, projects in project_scopes:
        if projects is None:
            continue
        if not isinstance(projects, list):
            raise SystemExit(f"数据校验失败：{path}必须是数组。")
        for index, project in enumerate(projects, start=1):
            if not isinstance(project, dict):
                raise SystemExit(f"数据校验失败：{path}第 {index} 项必须是对象。")
            amount = str(project.get("预计投入") or "").strip()
            payback = str(project.get("投资回报周期") or "").strip()
            if not any(character.isdigit() for character in amount) or "元" not in amount or "待" in amount:
                raise SystemExit(
                    f"数据校验失败：{path}第 {index} 项.预计投入必须填写包含金额单位的数值或区间，不得使用待补充。"
                )
            if (
                not any(character.isdigit() for character in payback)
                or not ("个月" in payback or "年" in payback)
                or "待" in payback
            ):
                raise SystemExit(
                    f"数据校验失败：{path}第 {index} 项.投资回报周期必须填写以月或年表示的数值或区间，不得使用待补充。"
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="智改数转报告远程生成客户端")
    parser.add_argument("--data", required=True, help="数据 JSON 文件路径")
    parser.add_argument("--output", required=True, help="输出 docx 文件路径")
    parser.add_argument("--api-base-url", default=os.environ.get("ZHIGAI_API_BASE_URL"), help="远程服务地址")
    parser.add_argument("--license-key", default=os.environ.get("ZHIGAI_LICENSE_KEY"), help="授权码")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="本地配置文件路径")
    parser.add_argument("--timeout", type=int, default=180, help="请求超时时间，单位秒")
    parser.add_argument("--save-config", action="store_true", help="保存本次服务地址和授权码到本地配置")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser()
    config = load_config(config_path)
    api_base_url = resolve_api_base_url(args.api_base_url, config)
    license_key = args.license_key or config.get("licenseKey")

    if not api_base_url:
        raise SystemExit("缺少远程服务地址。请传入 --api-base-url 或设置 ZHIGAI_API_BASE_URL。")
    if not license_key:
        raise SystemExit("缺少授权码。请传入 --license-key 或设置 ZHIGAI_LICENSE_KEY。")

    print("正在检查授权码状态...")
    license_status = request_license_status(api_base_url, license_key, args.timeout)
    require_active_license(license_status)

    data_path = Path(args.data).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    data = read_json(data_path)
    require_complete_pain_analysis(data)
    require_complete_maturity_analysis(data)
    require_complete_plan(data)
    files: dict[str, dict[str, str]] = {}
    remote_data = collect_uploads(data, files)

    payload = {
        "data": remote_data,
        "files": files,
        "outputFilename": output_path.name,
    }

    print(f"正在请求远程生成服务：{api_base_url.rstrip('/')}/generate")
    if files:
        print(f"已打包图片附件：{len(files)} 个")

    result = request_generate(api_base_url, license_key, payload, args.timeout)
    if not result.get("ok"):
        raise SystemExit(result.get("message") or result.get("error") or "远程生成失败")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(base64.b64decode(result["contentBase64"]))
    print(f"✅ 报告生成完成：{output_path}")

    logs = str(result.get("logs") or "").strip()
    if logs:
        print("\n--- 服务端生成日志 ---")
        print(logs)

    if args.save_config:
        save_config(config_path, api_base_url, license_key)
        print(f"已保存配置：{config_path}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
