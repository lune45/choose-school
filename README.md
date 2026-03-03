# 留学选校 AI 分析系统（MVP）

## 1. 当前能力概览
- 手机号注册/登录（验证码 + 密码）
- Landing 页 + 分步式报告创建流程
- 选校支持：内置列表多选 + Excel 识别
- 关注点页已升级为「选择 + 排序」两阶段交互（2-6 个维度）
- 权重由前端实时计算并提交，后端兼容旧版请求
- DeepSeek 报告生成（失败重试、结构化 JSON 规范化）
- 报告页结构化展示 + PDF 下载
- 管理员后台（学校数据管理、RAG 检索候选审批、memory 看板）
- 学校目录页（按 QS/USNews/THE 浏览学校与项目）

## 2. 技术栈
- 后端：FastAPI + SQLAlchemy + SQLite
- 前端：原生 HTML/CSS/JS（单页路由）
- AI：DeepSeek（chat + reasoner）
- 报告：ReportLab 生成 PDF

## 3. 启动方式（无 Docker）
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

浏览器访问：`http://127.0.0.1:8000`

## 4. 环境变量
见 [backend/.env.example](/Users/xi/mine/startup/3.2%2021dian/backend/.env.example)。

核心变量：
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_MODEL`（默认 `deepseek-chat`）
- `DEEPSEEK_REASONER_MODEL`（默认 `deepseek-reasoner`）
- `SEARCH_PROVIDER`（`auto`：serper -> tavily -> bing -> duckduckgo）
- `SERPER_API_KEY` / `TAVILY_API_KEY` / `BING_API_KEY`
- `ADMIN_PHONES`

## 5. 前端路由
- `/`：Landing
- `/login`：注册/登录
- `/app`：历史报告
- `/app/new`：Step1 基础信息
- `/app/concerns`：Step2 关注点（选择+排序）
- `/app/schools`：Step3 选校
- `/app/confirm`：Step4 确认并发起分析
- `/app/report/:id`：报告详情
- `/app/catalog`：学校目录
- `/app/catalog/school/:name`：学校详情
- `/app/catalog/program/:id`：项目详情
- `/app/admin`：管理员页（仅 admin）

## 6. Step2 关注点权重逻辑（新）
可选维度固定 13 个（`employment/salary/visa/ranking/cost/...`）。

交互分两阶段：
1. 选择：最少 2 个，最多 6 个
2. 排序：拖拽调整优先级（第 1 位权重最高）

权重公式（前端实时计算）：
- 设已选数量为 `N`
- 第 `i` 名权重：
  `round((N - i + 1) / (N*(N+1)/2) * 100)`
- 最后一名：
  `100 - 前面权重和`（修正取整误差）

验证样例：
- 2 个：`67/33`
- 3 个：`50/33/17`
- 5 个：`33/27/20/13/7`

## 7. 报告创建接口（新主入口）
### `POST /api/report/create`
请求体（前端当前会同时带新旧兼容字段）：
```json
{
  "country": "美国",
  "major": "CS",
  "budget_max": 70000,
  "concerns": ["employment", "salary", "visa"],
  "selected_dimensions": ["employment", "salary", "visa"],
  "weights": {"employment": 50, "salary": 33, "visa": 17},
  "schools": [1, 2, 3],
  "school_ids": [1, 2, 3]
}
```

兼容策略：
- 若传入 `weights` 且总和约等于 100（±3），后端直接采用
- 若不传（旧版客户端），后端回退原默认权重逻辑

保留兼容接口：
- `POST /api/analysis/run`

## 8. 数据库字段（本次相关）
### `analysis_records`
- `selected_dimensions`（兼容）
- `weights`（兼容）
- `concerns_json`（新增：按排序后的维度 key 数组）
- `weights_json`（新增：前端提交的用户权重）

### `school_programs`
- `query_output_json`：按 v2 规范落库的完整查询输出对象

说明：
- 应用启动时会自动执行轻量 SQLite migration（无 Alembic）

## 9. 关键 API 清单
- 认证：`/api/auth/*`
- 学校：`/api/countries`、`/api/schools`、`/api/schools/upload-excel`
- 目录：`/api/school-directory*`、`/api/school-programs/{id}`
- 报告：`/api/report/create`、`/api/report/{id}`、`/api/analysis/{id}/pdf`
- 管理员：`/api/admin/*`（学校管理、RAG 检索、审批、memory）

## 10. 开发验证命令
```bash
# backend
cd backend
.venv/bin/python -m compileall app

# frontend
cd ../frontend
node --check app.js
```

## 11. 备注
- 验证码接口在开发模式可返回 `debug_code`
- 选校 Excel 识别采用全表扫描 + 模糊匹配
- AI 失败会返回 `failed` 状态和错误信息，前端支持重新生成
