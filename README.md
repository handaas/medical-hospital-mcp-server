# 医院信息搜索

[该MCP服务提供医院关键词搜索、医院性质与等级筛选、院区地址、联系方式、科室及医院详细介绍查询功能。](https://www.handaas.com/)


## 主要功能

- 🔍 医院名称模糊搜索
- 🏥 医院性质、等级和专业类型筛选
- 📍 医院所在省市及院区地址查询
- 📞 医院联系方式与科室查询
- 🧾 医院介绍及运营主体核验

## 环境要求

- Python 3.10+
- 依赖包：python-dotenv, requests, mcp

## 本地快速启动

### 1. 克隆项目
```bash
git clone https://github.com/handaas/medical-hospital-mcp-server
cd medical-hospital-mcp-server
```

### 2. 创建虚拟环境&安装依赖

```bash
python -m venv mcp_env && source mcp_env/bin/activate
pip install -r requirements.txt
```

### 3. 环境配置

复制环境变量模板并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下环境变量：

```env
INTEGRATOR_ID=your_integrator_id
SECRET_ID=your_secret_id
SECRET_KEY=your_secret_key
HANDAAS_REQUEST_TIMEOUT=30
```

### 4. streamable-http启动服务

```bash
python server/mcp_server.py streamable-http
```

服务将在 `http://localhost:8000` 启动，MCP 地址为 `http://127.0.0.1:8000/mcp`。

#### 支持启动方式 stdio 或 sse 或 streamable-http

### 5. Cursor / Cherry Studio MCP配置

```json
{
  "mcpServers": {
    "medical-hospital-mcp-server": {
      "type": "streamableHttp",
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

## STDIO版安装部署

### 设置Cursor / Cherry Studio MCP配置

```json
{
  "mcpServers": {
    "medical-hospital-mcp-server": {
      "command": "uv",
      "args": ["run", "mcp", "run", "{workdir}/server/mcp_server.py"],
      "env": {
        "PATH": "{workdir}/mcp_env/bin:$PATH",
        "PYTHONPATH": "{workdir}/mcp_env",
        "INTEGRATOR_ID": "your_integrator_id",
        "SECRET_ID": "your_secret_id",
        "SECRET_KEY": "your_secret_key"
      }
    }
  }
}
```

## 使用官方Remote服务

### 1. 直接设置Cursor / Cherry Studio MCP配置

```json
{
  "mcpServers": {
    "medical-hospital-mcp-server":{
      "type": "streamableHttp",
      "url": "https://mcp.handaas.com/medical/hospital_bigdata?token={token}"
      }
  }
}
```

### 注意：integrator_id、secret_id、secret_key及token需要登录 https://www.handaas.com/ 进行注册开通平台获取


## 可用工具

### 1. medical_hospital_search
**功能**: 医院信息搜索

**参数**:
传入医院名称、性质、等级、专业类型或省份等条件，分页查询符合条件的医院。

- `hospitalName` (可选): 医院名称关键词，支持模糊搜索
- `hospitalType` (可选): 医院性质，例如公立、民营
- `hospitalLevel` (可选): 医院等级，例如三甲、二甲、三级
- `hospitalProfessionalType` (可选): 专业类型，例如综合医院、儿童医院
- `hospitalProvince` (可选): 省份短名，例如北京、广东
- `pageIndex` (可选): 页码，从1开始，默认1
- `pageSize` (可选): 每页条数，默认10，最大50

**返回值**:
- `total`: 符合条件的医院总数
- `resultList`: 医院结果列表
  - `hospitalId`: 医院ID，供详情查询使用
  - `hospitalName`: 医院名称
  - `hospitalLevel`: 医院等级
  - `hospitalType`: 医院性质
  - `hospitalProfessionalType`: 专业类型
  - `hospitalProvince`: 所在省份
  - `hospitalCity`: 所在城市
  - `hospitalDistrict`: 所在区县
  - `hospitalAddressDetail`: 院区地址列表
  - `hospitalDepartment`: 科室列表
  - `hospitalDepartmentCount`: 科室数量
  - `hospitalCampusCount`: 院区数量
  - `operatingEntity`: 运营主体
  - `nameId`: 运营主体ID

### 2. medical_hospital_detail
**功能**: 医院信息详情查询

**参数**:
通过医院搜索返回的医院ID查询单家医院的完整信息。

- `hospitalId` (必需): 必须使用 `medical_hospital_search` 返回的 `hospitalId`

**返回值**:
- `total`: 命中数量，通常为1
- `resultList`: 医院详情列表
  - `hospitalName`: 医院名称
  - `hospitalIntroduction`: 医院简介
  - `hospitalDesc`: 医院详细介绍
  - `hospitalAddressDetail`: 各院区名称、地址及经纬度
  - `hospitalContact`: 联系方式及联系方式类型
  - `hospitalDepartment`: 科室列表
  - `hospitalLevel`: 医院等级
  - `hospitalType`: 医院性质
  - `operatingEntity`: 运营主体
  - `nameId`: 运营主体ID

## 使用注意事项

1. **医院ID要求**: 详情查询必须使用医院搜索结果中的 `hospitalId`，不能使用医院名称代替。
2. **省份筛选**: `hospitalProvince` 使用北京、广东等短名，不带省、市后缀。
3. **API限制**: 分页查询一页最多获取50条数据。
4. **合法空结果**: 未命中时返回 `total=0` 和 `resultList=[]`。
5. **医疗边界**: 本服务只提供医院信息，不提供挂号、诊断、处方或紧急医疗服务。

## 使用提问示例

### medical_hospital_search (医院信息搜索)
1. 搜索北京的三甲综合医院
2. 帮我查找名称中包含“协和”的医院
3. 查询广东省内的儿童医院

### medical_hospital_detail (医院信息详情查询)
1. 查看刚才医院的院区地址和联系电话
2. 查询这家医院有哪些科室
3. 获取该医院的完整介绍和运营主体

## 测试验证

```bash
python -m py_compile server/mcp_server.py
python -m unittest discover -s tests -v
```

当前服务包含 5 个离线单元测试。真实接口验证需在本地 `.env` 配置有效凭据后执行，测试输出不得提交真实业务响应或凭据。
