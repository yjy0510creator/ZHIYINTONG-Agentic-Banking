# Windows 从零部署

## 1 环境
已实际验证：Windows，Python 3.13.12，Node.js 26.13.0（含 npm）。依赖使用本包固定版本；其他 Python/Node 版本未在本次重新验证。请将 Python 与 Node 加入 PATH，执行 python --version、node --version、npm --version 核对。安装依赖需要访问对应官方包仓库；本包不包含运行时、.venv 或 node_modules。

## 2 安装
在新目录解压本包，不覆盖原项目；PowerShell 切换到解压根目录。
```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
backend/.venv/Scripts/python.exe -m pip check
npm --prefix frontend ci
```
requirements-dev 包含运行依赖、MCP 与 pytest/httpx。若包源未提供固定版本，应报告安装阻塞，不擅自整体升级依赖。

## 3 本地开发身份与数据库
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/configure-demo.ps1
```
脚本仅在不存在 backend/.env 时运行，生成三个独立随机口令并写入本机文件。前端仅配置公开 API 地址，不放任何口令。请在本机编辑器查看 backend/.env 获取 Maker/Checker 口令，勿截图或公开提交。默认演示账户10000元、受保护预留6000元；不要为了演示大额交易改原账户。

backend/.env 的 BANKING_DB_PATH 指向该解压目录的 backend/data/demo.db。数据库结构由 initialize_database.py 创建；新模拟账户按首次业务访问惰性建立，策略表在首次授权阶段初始化。无真实银行数据迁移或导入。空 OPENAI_API_KEY 可用，语言理解回退确定性技能。

## 4 启动
两个 PowerShell 窗口分别执行：
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-backend.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-frontend.ps1
```
后端独立端口8088，前端3088，避免干扰既有8000/3000。访问 http://localhost:3088；健康检查 http://127.0.0.1:8088/health；接口 http://127.0.0.1:8088/docs 和 /openapi.json。关闭本次窗口即可停止本次进程。

## 5 构建和测试
```powershell
npm --prefix frontend run build
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1
```
生产构建后可在 frontend 执行 npm run start -- --port 3088。注意“生产构建”仅指 Next.js 优化构建，不意味着后端获得生产身份或银行认证。APP_ENV=production 会拒绝开发账号，未集成 IdP 前不可作为真实业务服务开放。

## 排障
- 401：使用本解压实例的开发口令；会话过期后重新登录，不复制旧Token。
- 503 Production identity provider：检查是否明确配置 development，仅限本机模拟。
- 403/409：检查 Maker、MFA有效期、Checker、原计划摘要和 POLICY_STALE；不能通过改数据库恢复审批。
- 端口占用：更改独立端口，并同步 NEXT_PUBLIC_API_BASE_URL、CORS_ORIGINS；更改前端环境变量后重启。
- 余额不足：默认预留后仅4000元可用，50001元演示必须使用独立测试夹具，不修改原账本。
- 数据库路径/权限：确保新 data 目录可写，不使用只读压缩包内部路径。
- 中文路径或包安装异常：尝试较短的英文解压路径，保留固定依赖；记录实际错误，不伪报安装成功。
- 在线模型超时：可保持空Key使用本地回退，不能把回退结果描述为在线模型输出。
