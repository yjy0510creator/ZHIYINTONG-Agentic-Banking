# ZHIYINTONG V3.1 最终金融安全验收

**最终结论：PASS（比赛本地模拟系统安全验收，不代表真实银行生产认证）。**

| 批次/范围 | 总数 | 通过 | 失败 | 错误 | 跳过 |
|---|---:|---:|---:|---:|---:|
| 43 | 43 | 43 | 0 | 0 | 0 |
| 55 | 55 | 55 | 0 | 0 | 0 |
| 70 | 70 | 70 | 0 | 0 | 0 |
| full | 90 | 90 | 0 | 0 | 0 |
| original70 | 70 | 70 | 0 | 0 | 0 |
| new | 20 | 20 | 0 | 0 | 0 |

| 全量测试文件 | 总数 | 通过 | 失败 | 错误 | 跳过 |
|---|---:|---:|---:|---:|---:|
| backend/tests/test_banking_v3.py | 41 | 41 | 0 | 0 | 0 |
| backend/tests/test_final_security_audit.py | 15 | 15 | 0 | 0 | 0 |
| backend/tests/test_intelligence.py | 12 | 12 | 0 | 0 | 0 |
| backend/tests/test_policy_binding_v31.py | 20 | 20 | 0 | 0 | 0 |
| backend/tests/test_security_acceptance.py | 2 | 2 | 0 | 0 | 0 |

43、55、70 是分别重新执行的历史范围；original70 和 new 是本次全量批次的互斥子集。它们相互包含，**不得将43+55+70+新增数相加当作独立用例数量**。完整独立总数以 full 行为准。原有四个测试文件未改，失败测试未删除、跳过或降低断言。XML 和源码 SHA256 对比已保存。

## 修复与数据保护

- backend/services/policy_service.py：新增服务端策略指纹/代次、不可变授权快照、策略失效审计。
- backend/services/sandbox_service.py：计划摘要补齐版本、指纹、代次和风险标记。
- backend/services/execution_gateway.py：各授权阶段快照校验、Maker/MFA摘要与有效期、Checker完整审批绑定、最终原子校验及审计。
- backend/services/api_v3.py：成功execute完成审计由网关事务负责，避免提交后审计失败窗口。
- backend/services/database.py：连接上下文结束时显式关闭 SQLite 连接，避免悬挂连接影响 WAL 释放与进程重启证据读取。
- backend/tests/test_policy_binding_v31.py：新增独立进程、真实HTTP、临时数据库安全测试。

修改前源码备份：backups/agentic_banking_3.1/pre-fix-source.zip；完整清单 source-sha256.json。测试源码与最终交付源码逐字节一致。正式两份既有数据库全部表的行数及内容哈希前后核对见 production-data-comparison.json；没有删除审计历史、调整余额或预留。新策略激活未在正式数据库上执行。

用户已明确允许最终写回时自动重载一次；没有手动停止8000服务。前端通过同盘隔离目录执行生产构建，未覆盖运行中的 .next；UI、精灵、DAG源文件未修改。pip check：No broken requirements found；独立卡片回退检查通过。API兼容版本3.0.0保持不变，V3.1为本次安全修订版本。

## 复现与证据

所有Python命令使用项目 backend/.venv3/Scripts/python.exe。为避免旧测试覆盖历史证据，测试在逐字节副本中运行，最终源文件SHA一致。

全量（副本backend目录）：
```powershell
python -m pytest tests -q --tb=short --basetemp=C:/Users/16/AppData/Local/Temp/zhiyintong-v31-acceptance-v2 --junitxml=test-results/v31-acceptance.xml
```
43项（regression-43/backend）：`python -m pytest tests/test_banking_v3.py tests/test_security_acceptance.py -q --tb=short --basetemp=C:/Users/16/AppData/Local/Temp/zhiyintong-v31-reg43-v2 --junitxml=test-results/regression43.xml`。
55项（regression-55/backend）：`python -m pytest tests/test_banking_v3.py tests/test_security_acceptance.py tests/test_intelligence.py -q --tb=short --basetemp=C:/Users/16/AppData/Local/Temp/zhiyintong-v31-reg55-v2 --junitxml=test-results/regression55.xml`。
70项（regression-70/backend）：`python -m pytest tests/test_banking_v3.py tests/test_security_acceptance.py tests/test_intelligence.py tests/test_final_security_audit.py -q --tb=short --basetemp=C:/Users/16/AppData/Local/Temp/zhiyintong-v31-reg70-v2 --junitxml=test-results/regression70.xml`。
前端：在 backups/agentic_banking_3.1/frontend-build 运行 `npm run build`。原依赖复用，未升级依赖。

完整证据目录：[backend/test-results/v31-security](backend/test-results/v31-security)。full下含全量XML、HTTP JSON、子进程日志；regression-43/55各自保留独立结果。专项覆盖包括MCP写入口阻断、幂等并发、审计链、真实后端进程重启持久性、Maker-Checker和六大场景。

## 中间失败如实保留

首次隔离运行因临时目录父级未建立出现52个setup error（18 passed）；修正目录后一次运行87 passed但2个SQLite证据收集teardown error。随后延迟初始化接入过程的一次专项批次5 failed、13 passed、1 error，属于未完成接入的中间版本；没有将这些批次标为通过。跨盘前端依赖链接导致的首次build失败也保留；改同盘隔离构建后重跑。最终结论仅依据最终冻结源码与最终批次，不用中间结果覆盖或替代最终结果。

## 安全边界

全部资金变动均为临时独立模拟账本。真实银行、真实生物识别、生产身份提供方以及组织层面的两位自然人隔离：NOT VERIFIED，不宣称生产认证或比赛名次。比赛演示中的RED ALLOW仍只表示局部TrustEngine判断，执行许可由网关完整授权状态决定。

配套报告：[策略版本绑定](POLICY_VERSION_BINDING_AUDIT.md)、[负向安全测试](NEGATIVE_SECURITY_TEST_REPORT.md)、[Maker-Checker](MAKER_CHECKER_AUDIT_REPORT.md)。

## 在线审计追加与数据保护判定

**不是数据库所有表完全不变。** 首次将所有表哈希直接判等得到FAIL；该原始报告保留在证据目录 initial-whole-database-comparison.md。只读逐条调查确认：业务表全部相同，原历史审计前缀逐字相同；在线服务新增的全是过期会话认证拒绝，自动序列随审计追加增长。没有资金执行，没有改写或清除历史审计。

| 数据库 | 全表相同 | 业务表相同 | 原审计前缀相同 | 新增认证拒绝审计 |
|---|---|---|---|---:|
| `D:\zhiyintong-web\backend\data\zhiyintong_audit.db` | False | True | True | 1138 |
| `D:\zhiyintong-web\backend\test-results\ui-large.db` | True | True | True | 0 |

新增审计从2026-11-01 16:08:38北京时间开始，早于16:18:37最终写回后的重载，涉及/api/audit-logs、/api/audit-stream及旧工作流stream。路径及规律与前端过期会话轮询/重连一致，但审计未记录请求进程，不能仅凭路径确定来源。详见 live-audit-growth.json（最初调查快照）和 audit-append-snapshot-0.json（与上表同一只读事务的完整新增记录），保留实际事件ID和时间。在线服务继续追加日志，不能将不同时间快照的计数误当矛盾。

本报告PASS指最终要求的**生产业务数据一致、历史审计未改且全部关键安全测试通过**；若将“不修改数据库”理解为运行期间连正常新增审计都禁止，则这一更强的“数据库完全静止”条件**未满足**，不得把本报告作为数据库全表不变证明。没有为了得到PASS删除、修改或阻断这些审计记录。
