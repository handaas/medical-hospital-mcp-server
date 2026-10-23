"""医疗医院信息搜索 MCP 服务离线测试。"""

import asyncio
import importlib.util
import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

SERVER_PATH = Path(__file__).parents[1] / "server" / "mcp_server.py"
SPEC = importlib.util.spec_from_file_location("medical_hospital_mcp_server", SERVER_PATH)
assert SPEC and SPEC.loader
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


class ContractTests(TestCase):
    def test_registered_tools_and_annotations(self) -> None:
        tools = asyncio.run(server.mcp.list_tools())
        self.assertEqual(server.mcp.name, '医院信息搜索')
        self.assertEqual({tool.name for tool in tools}, {"medical_hospital_search", "medical_hospital_detail"})
        for tool in tools:
            self.assertEqual(tool.outputSchema.get("type"), "object")
            self.assertTrue(tool.annotations.readOnlyHint)
            self.assertFalse(tool.annotations.destructiveHint)
            self.assertTrue(tool.annotations.idempotentHint)
            self.assertGreaterEqual(len(tool.description or ""), 50)

    def test_product_ids_are_scoped_to_hospital_capabilities(self) -> None:
        self.assertEqual(server.PRODUCT_IDS, {
            "hospital_search": "6a7b07b28c8d379dd486b944",
            "hospital_detail": "6a7b0e85dfa4a2f37b191128",
        })

    def test_missing_credentials_and_empty_result(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch.object(server.requests, "post") as post:
            self.assertEqual(server.call_api("product", {}), {"error": "INTEGRATOR_ID 未配置"})
        post.assert_not_called()
        response = Mock(status_code=200)
        response.json.return_value = {"code": "10001", "msgCN": "查询数据为空"}
        credentials = {"INTEGRATOR_ID": "id", "SECRET_ID": "sid", "SECRET_KEY": "key"}
        with patch.dict(os.environ, credentials, clear=True), patch.object(server.requests, "post", return_value=response):
            self.assertEqual(server.call_api("product", {}), {"total": 0, "resultList": []})


class RoutingTests(TestCase):
    def test_search_and_detail_routes(self) -> None:
        with patch.object(server, "call_api", return_value={"dataList": [], "dataTotal": 0}) as call:
            self.assertEqual(server.medical_hospital_search(hospitalName="协和"), {"total": 0, "resultList": []})
        self.assertEqual(call.call_args.args[0], server.PRODUCT_IDS["hospital_search"])

        with patch.object(server, "call_api", return_value={}) as call:
            self.assertEqual(server.medical_hospital_detail("hospital-1"), {"total": 0, "resultList": []})
        call.assert_called_once_with(server.PRODUCT_IDS["hospital_detail"], {"hospitalId": "hospital-1"})

    def test_pagination_validation(self) -> None:
        with patch.object(server, "call_api") as call:
            result = server.medical_hospital_search(pageSize=51)
        self.assertEqual(result["parameter"], "pageSize")
        call.assert_not_called()
