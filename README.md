# 留学选校 AI 分析系统（MVP）

## 功能范围
- 国内手机号注册登录（验证码 + 密码）
- 国家选择 + 关注维度多选（动态权重）
- 从数据库选校 + Excel自动识别选校
- AI分析（DeepSeek）
- 网页展示结果 + PDF下载
- 管理员后台（学校项目增删改查 + Excel批量导入）

## 技术栈
- 后端：FastAPI + SQLAlchemy + SQLite
- 前端：原生 HTML/CSS/JS 单页
- 报告：ReportLab 生成 PDF

## 目录结构
- `backend/app/main.py`：API入口
- `backend/app/routers/`：认证、学校、分析接口
- `backend/app/services/`：权重、评分、Excel匹配、DeepSeek、PDF
- `frontend/`：页面与交互

## 启动方式（不使用 Docker）
1. 创建并激活虚拟环境
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
# 在 .env 中设置 DEEPSEEK_API_KEY
# ADMIN_PHONES 用逗号分隔可设管理员手机号，如 13800000000,13900000000
```

4. 启动服务
```bash
uvicorn app.main:app --reload --port 8000
```

5. 打开页面
- 浏览器访问：`http://127.0.0.1:8000`

## 说明
- 当前短信验证码接口为开发占位，会在返回中包含 `debug_code`（可在 `.env` 关闭）。
- Excel识别策略是“全表扫描 + 模糊匹配学校名”，不依赖固定列名或行位置。
- AI调用失败会返回 `failed` 状态和错误信息，可在前端触发“重新生成”。
- 管理员接口仅保留后端API（`/api/admin/*`），不在普通用户前端展示。
- 管理员可下载导入模板：`/api/admin/schools/template`。

## 下一步建议
- 对接真实短信服务（阿里云/腾讯云）
- 增补学校项目数据库字段与数据量
- 完善管理员后台（操作审计、字段校验、权限分级）
