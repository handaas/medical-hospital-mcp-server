# 医疗：医院信息搜索

[该 MCP 服务提供医院搜索和医院详情查询能力，帮助用户发现医疗机构并核验院区、科室、联系方式、医院介绍和运营主体。](https://www.handaas.com/)

## 主要功能

- 🏥 医院名称模糊搜索
- 🏷️ 医院性质、等级和专业类型筛选
- 📍 省份、城市和院区地址查询
- 📞 医院联系方式与科室查询
- 🧾 医院详细介绍和运营主体核验

## 推荐调用流程

1. 用户只提供医院名称、地区或等级时，先调用 `medical_hospital_search`。
2. 从候选结果中确认医院，并取得 `hospitalId`。
3. 调用 `medical_hospital_detail` 查询该医院的院区、联系方式、科室和完整介绍。

不要使用医院名称代替 `hospitalId` 调用详情 Tool，也不要自行构造医院 ID。

## 服务设计说明

- 服务仅提供医院信息相关的 2 个只读 Tool。
- 所有成功响应统一使用 `total/resultList` 顶层；详情命中时通常 `total=1`。
- 业务码 `10001 查询数据为空` 归一化为 `total=0`、`resultList=[]`，不作为系统错误。
- Tool 不提供在线挂号、诊疗建议、预约、支付或写入能力。

## 环境要求

- Python 3.10+
- 依赖：`mcp`、`python-dotenv`、`requests`

## 本地快速启动

```bash
cd medical-hospital-mcp-server
python3 -m venv mcp_env
source mcp_env/bin/activate
pip install -r requirements.txt
cp .env.example .env
python server/mcp_server.py streamable-http
```

服务默认地址：`http://127.0.0.1:8000/mcp`。支持 `stdio`、`sse` 和 `streamable-http`。

## 环境变量

```env
INTEGRATOR_ID=your_integrator_id
SECRET_ID=your_secret_id
SECRET_KEY=your_secret_key
HANDAAS_REQUEST_TIMEOUT=30
```

## 可用 Tool 与 Product ID

| MCP Tool | 使用场景 | Product ID | 关键输入 |
| --- | --- | --- | --- |
| `medical_hospital_search` | 按名称、性质、等级、专业类型和省份发现医院 | `6a7b07b28c8d379dd486b944` | 医院筛选条件、分页 |
| `medical_hospital_detail` | 查询单家医院的院区、联系方式、科室和详细介绍 | `6a7b0e85dfa4a2f37b191128` | `hospitalId` |

## Tool 详细说明

### 1. medical_hospital_search

**何时使用**：用户询问某家医院、某地区医院、某等级医院或某类专科医院时使用，也是详情查询的入口。

**关键参数**：

- `hospitalName`：医院名称关键词，支持模糊搜索，例如“协和”。
- `hospitalType`：医院性质，例如“公立”或“民营”。
- `hospitalLevel`：医院等级，例如“三甲”“二甲”“三级”。
- `hospitalProfessionalType`：专业类型，例如“综合医院”“儿童医院”。
- `hospitalProvince`：所在省份筛选值，使用“北京”“广东”等短名，不带“省”“市”后缀。
- `pageIndex`：从 1 开始；`pageSize` 默认 10、最大 50。

**返回说明**：返回医院名称、等级、性质、专业类型、地区、院区、科室和运营主体等摘要。后续详情查询使用结果中的 `hospitalId`。

### 2. medical_hospital_detail

**何时使用**：已经通过搜索确认医院，需要查看完整院区、联系方式、科室或医院介绍时使用。

**关键参数**：

- `hospitalId`：必填，必须来自 `medical_hospital_search` 的结果。

**返回说明**：命中时返回单条医院详情，包括院区地址、联系电话、科室、详细介绍和运营主体。

## 使用示例

### 示例一：搜索医院

用户问题：

> 搜索北京的三甲综合医院，先返回 5 家。

建议调用：

```json
{
  "tool": "medical_hospital_search",
  "arguments": {
    "hospitalLevel": "三甲",
    "hospitalProfessionalType": "综合医院",
    "hospitalProvince": "北京",
    "pageIndex": 1,
    "pageSize": 5
  }
}
```

### 示例二：查询医院详情

用户问题：

> 查看刚才确认医院的院区地址、联系电话和科室。

建议调用：

```json
{
  "tool": "medical_hospital_detail",
  "arguments": {
    "hospitalId": "从医院搜索结果取得"
  }
}
```

## 使用注意事项

1. 搜索结果可能包含名称相近的不同医院，必须先核对地区和医院等级。
2. `hospitalId` 只能来自医院搜索结果。
3. 空结果是合法业务结果，可减少筛选条件后再次搜索。

## 测试验证

```bash
python -m py_compile server/mcp_server.py
python -m unittest discover -s tests -v
```

单元测试使用 Mock 响应；真实验证通过本地 `.env` 调用 HandaaS Integrator Gateway。
