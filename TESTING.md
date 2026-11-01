# 测试与复现
冻结验收90/90通过，0失败/错误/跳过。以下命令在backend目录使用虚拟环境Python执行；先安装requirements-dev.txt。请在本包解压副本复核，避免覆盖历史输出。临时目录使用全新路径，父目录需存在。子进程端口由测试选择，不停止8000服务。
```powershell
python -m pytest tests -q --tb=short --junitxml=test-results/recheck90.xml
python -m pytest tests/test_banking_v3.py tests/test_security_acceptance.py -q --junitxml=test-results/recheck43.xml
python -m pytest tests/test_banking_v3.py tests/test_security_acceptance.py tests/test_intelligence.py -q --junitxml=test-results/recheck55.xml
python -m pytest tests/test_banking_v3.py tests/test_security_acceptance.py tests/test_intelligence.py tests/test_final_security_audit.py -q --junitxml=test-results/recheck70.xml
python -m pytest tests/test_policy_binding_v31.py -q --junitxml=test-results/recheck20.xml
python -m pip check
```
前端：在frontend运行npm ci，再npm run build。当前package.json不提供正式lint可用性保证，不用不存在的检查冒充通过。

|文件|用例数|
|---|---:|
|test_banking_v3.py|41|
|test_security_acceptance.py|2|
|test_intelligence.py|12|
|test_final_security_audit.py|15|
|test_policy_binding_v31.py|20|

43⊂55⊂70⊂90。20为新策略专项，与原70不重叠。不要把所有批次相加。
覆盖Maker/Checker隔离、拒绝终态、绕过、重放、并发幂等、MFA缺失/过期、策略变化/指纹变化/回滚/竞争、审计故障、哈希链、重启持久性、MCP入口等。精确测试名见evidence/test-inventory.json。
历史中间失败记录不代表最终冻结结果，原始报告未删除。证据目录仅选用最终XML与合成HTTP；完整历史调查保留于原项目，不把私有业务库装入包内。
