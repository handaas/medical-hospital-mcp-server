
"""HandaaS 医院信息搜索 MCP 服务。"""

import json
import os
import sys
from hashlib import md5
from typing import Any, Literal
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations


load_dotenv()

mcp = FastMCP(
    "医疗：医院信息搜索",
    instructions='先按医院名称、类型、等级、专业类型或省份检索，再使用返回的 hospitalId 查询院区、科室、联系方式与完整简介。',
    dependencies=["python-dotenv", "requests"],
)

GATEWAY_BASE_URL = "https://console.handaas.com/api/v1/integrator/call_api"
DEFAULT_TIMEOUT_SECONDS = 30.0

PRODUCT_IDS = {'hospital_search': '6a7b07b28c8d379dd486b944', 'hospital_detail': '6a7b0e85dfa4a2f37b191128'}

READ_ONLY_TOOL = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


def _request_timeout() -> float:
    raw = os.environ.get("HANDAAS_REQUEST_TIMEOUT", "")
    try:
        value = float(raw) if raw else DEFAULT_TIMEOUT_SECONDS
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_TIMEOUT_SECONDS


def _credential(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    if not value or value.startswith("your_"):
        return None
    return value


def _compact_params(params: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None}


def _build_signature(call_params: dict[str, str], secret_key: str) -> str:
    plain = "".join(str(call_params[key]) for key in sorted(call_params))
    return md5(f"{plain}{secret_key}".encode("utf-8")).hexdigest()


def call_api(product_id: str, params: dict[str, Any]) -> Any:
    """调用 HandaaS Integrator Gateway并返回业务 data。"""
    integrator_id = _credential("INTEGRATOR_ID")
    secret_id = _credential("SECRET_ID")
    secret_key = _credential("SECRET_KEY")
    if not integrator_id:
        return {"error": "INTEGRATOR_ID 未配置"}
    if not secret_id:
        return {"error": "SECRET_ID 未配置"}
    if not secret_key:
        return {"error": "SECRET_KEY 未配置"}
    if not product_id:
        return {"error": "Product ID 不能为空"}

    call_params = {
        "product_id": product_id,
        "secret_id": secret_id,
        "params": json.dumps(
            _compact_params(params), ensure_ascii=False, separators=(",", ":")
        ),
    }
    call_params["signature"] = _build_signature(call_params, secret_key)
    url = f"{GATEWAY_BASE_URL}/{quote(integrator_id, safe='')}"
    try:
        response = requests.post(url, data=call_params, timeout=_request_timeout())
    except requests.RequestException:
        return {"error": "HandaaS 网关请求失败，请稍后重试"}
    if response.status_code != 200:
        return {
            "error": "HandaaS 网关返回非成功状态",
            "statusCode": response.status_code,
        }
    try:
        payload = response.json()
    except (ValueError, requests.exceptions.JSONDecodeError):
        return {"error": "HandaaS 网关返回了无法解析的响应"}
    if not isinstance(payload, dict):
        return {"error": "HandaaS 网关返回格式异常"}
    if "data" in payload:
        return payload["data"]
    error = payload.get("msgCN") or payload.get("message") or "HandaaS 网关未返回 data"
    if str(payload.get("code")) == "10001" or error == "查询数据为空":
        return {"total": 0, "resultList": []}
    result = {"error": error}
    if payload.get("code") is not None:
        result["code"] = payload["code"]
    return result


def _unwrap_backend_data(result: Any) -> Any:
    """兼容 Product API直接返回业务 data或保留内部 stat/data 外层。"""
    if not isinstance(result, dict) or "error" in result:
        return result
    if "stat" not in result:
        return result
    if result.get("stat") != 1:
        return {
            "error": result.get("msg") or "上游数据接口返回失败",
            "code": result.get("err"),
        }
    return result.get("data")


def _pagination_error(page_index: int, page_size: int, maximum: int = 50) -> dict[str, Any] | None:
    if page_index < 1:
        return {"error": "pageIndex 必须大于等于 1", "parameter": "pageIndex"}
    if page_size < 1 or page_size > maximum:
        return {"error": f"pageSize 必须在 1 到 {maximum} 之间", "parameter": "pageSize"}
    return None


def _normalize_paged(result: Any) -> Any:
    result = _unwrap_backend_data(result)
    if not isinstance(result, dict) or "error" in result:
        return result
    if isinstance(result.get("resultList"), list):
        records = result["resultList"]
        total = result.get("total", len(records))
        return {"total": total, "resultList": records}
    if isinstance(result.get("dataList"), list):
        records = result["dataList"]
        total = result.get("dataTotal", result.get("dataCount", len(records)))
        return {"total": total, "resultList": records}
    return result


def _normalize_single(result: Any) -> Any:
    result = _unwrap_backend_data(result)
    if not isinstance(result, dict) or "error" in result:
        return result
    if set(result) == {"total", "resultList"} and isinstance(result.get("resultList"), list):
        return result
    if not result:
        return {"total": 0, "resultList": []}
    return {"total": 1, "resultList": [result]}


def _number_range_error(
    minimum: int | float | None,
    maximum: int | float | None,
    minimum_name: str,
    maximum_name: str,
) -> dict[str, Any] | None:
    if minimum is not None and maximum is not None and minimum > maximum:
        return {
            "error": f"{minimum_name} 不能大于 {maximum_name}",
            "parameter": minimum_name,
        }
    return None


def _date_range_error(
    start: str | None,
    end: str | None,
    start_name: str,
    end_name: str,
) -> dict[str, Any] | None:
    if start and end and start > end:
        return {
            "error": f"{start_name} 不能晚于 {end_name}",
            "parameter": start_name,
        }
    return None

@mcp.tool(
    title="医院信息搜索",
    description=(
        "按医院名称、性质、等级、专业类型和省份发现医院。hospitalName 支持模糊搜索；"
        "hospitalType 可使用公立或民营，hospitalLevel 可使用三甲、二甲、三级等；省份筛选使用北京、广东等短名。"
        "pageIndex 从 1 开始，pageSize 最大 50；返回 total 与 resultList，并提供 hospitalId 供详情查询。"
    ),
    annotations=READ_ONLY_TOOL,
)
def medical_hospital_search(
    hospitalName: str | None = None,
    hospitalType: str | None = None,
    hospitalLevel: str | None = None,
    hospitalProfessionalType: str | None = None,
    hospitalProvince: str | None = None,
    pageIndex: int = 1,
    pageSize: int = 10,
) -> dict[str, Any]:
    """按名称、类型、等级、专业类型和省份分页检索医院。"""
    if error := _pagination_error(pageIndex, pageSize):
        return error
    return _normalize_paged(call_api(PRODUCT_IDS["hospital_search"], locals()))


@mcp.tool(
    title="医院信息详情查询",
    description=(
        "查询单家医院的院区地址、联系方式、科室、完整介绍和运营主体。"
        "hospitalId 必须取自 medical_hospital_search 的结果；详情统一返回 total 与 resultList。"
    ),
    annotations=READ_ONLY_TOOL,
)
def medical_hospital_detail(hospitalId: str) -> dict[str, Any]:
    """按医院检索返回的医院 ID查询联系方式、院区、科室和简介。"""
    return _normalize_single(call_api(PRODUCT_IDS["hospital_detail"], {"hospitalId": hospitalId}))


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    transport = arguments[0] if arguments else "stdio"
    if transport not in {"stdio", "sse", "streamable-http"}:
        print("启动方式必须是 stdio、sse 或 streamable-http", file=sys.stderr)
        return 2
    mcp.run(transport=transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
