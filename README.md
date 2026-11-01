# 智银通 ZHIYINTONG V3.1

可信自主银行智能体比赛交付版。当前系统仅连接独立模拟账本，不连接真实银行；开发身份与 MFA 均为模拟。

## 快速开始
先阅读 INSTALL.md。Windows 已验证 Python 3.13.12、Node.js 26.13.0。安装依赖后运行 scripts/configure-demo.ps1，再分别启动后端和前端。安全默认配置为 production（拒绝未配置的生产身份）；configure-demo.ps1 仅在新的解压目录创建独立开发配置，不覆盖已有 .env。

## 目录
- frontend：Next.js / React 页面、组件、精灵资源、DAG 与业务卡片。
- backend：FastAPI、Agent/MCP、服务端安全网关、模拟账本、策略与审计。
- backend/tests：完整 90 项测试源码。
- evidence：最终冻结验收 XML、合成 HTTP 证据与报告；不包含业务数据库或会话令牌。
- scripts：Windows 配置、启动与测试脚本。

## 验收口径
完整批次 90/90；历史 43、55、70 批次分别通过但相互包含。0失败、0错误、0跳过。详见 TESTING.md。API兼容版本仍3.0.0，前端package版本仍1.0.0；V3.1为项目安全修订版，不擅改兼容标识。

本包保留核心源文件字节内容，SOURCE_ORIGIN_SHA256.json 可核对来源。图形资源沿用项目现有素材；本次未独立核验原素材的第三方授权凭证，正式公开传播前应由权利人确认。未授予额外开源许可，也未发布至公开仓库。
