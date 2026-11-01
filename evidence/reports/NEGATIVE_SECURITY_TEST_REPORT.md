# V3.1 负向安全测试报告

全部 HTTP 请求发往随机端口的独立进程和临时 SQLite 数据库；不调用真实银行或模型 API。MFA 是开发环境模拟验证。完整请求体、响应体、审计事件及账本记录见每例 JSON；登录密码与 Bearer token 不输出。

## test_audit_failure_rolls_back_every_effect[api_request_completed] — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_audit_failure_rolls_back_every_effect_api_request_completed.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/e15ad80b15f249e395cd65201b65f4ea/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/e15ad80b15f249e395cd65201b65f4ea/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/e15ad80b15f249e395cd65201b65f4ea/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/e15ad80b15f249e395cd65201b65f4ea/human-review` | 200 | `{"state": "APPROVED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/e15ad80b15f249e395cd65201b65f4ea/execute` | 503 | `{"detail": "Audit unavailable; writes are blocked"} ` |

预期与断言：在临时DB中故障注入指定审计事件插入失败，execute=503，余额不变、账本0、执行事件0，审计链仍可验证。

实测补充：`[]`。

账本行数：0；审计链验证结果：`75a13641f67401c1c3f4bdb3ce494a392274c3c3f664c2547796f05da9437d24`。

- `e4a86faa84e44992b68c9844138cff42`，sequence=23，human_review_completed / APPROVE，workflow=e15ad80b15f249e395cd65201b65f4ea。

## test_audit_failure_rolls_back_every_effect[execution_completed] — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_audit_failure_rolls_back_every_effect_execution_completed.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/593835799f4246bcacac1ea0ee33f52e/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/593835799f4246bcacac1ea0ee33f52e/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/593835799f4246bcacac1ea0ee33f52e/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/593835799f4246bcacac1ea0ee33f52e/human-review` | 200 | `{"state": "APPROVED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/593835799f4246bcacac1ea0ee33f52e/execute` | 503 | `{"detail": "Audit unavailable; writes are blocked"} ` |

预期与断言：在临时DB中故障注入指定审计事件插入失败，execute=503，余额不变、账本0、执行事件0，审计链仍可验证。

实测补充：`[]`。

账本行数：0；审计链验证结果：`dde61bf8c0755d14b72e5176bc020f8bd55199d8f6cb9dcb8a8158d9f359d86c`。

- `3476f495de5e46798765c88a704aa433`，sequence=23，human_review_completed / APPROVE，workflow=593835799f4246bcacac1ea0ee33f52e。

## test_checker_different_transaction — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_checker_different_transaction.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/10fae9c984e04da9afab669ab453e1bf/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/10fae9c984e04da9afab669ab453e1bf/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/10fae9c984e04da9afab669ab453e1bf/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/08fe5515cf8645c9a128dc8dcb4bf463/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/08fe5515cf8645c9a128dc8dcb4bf463/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/08fe5515cf8645c9a128dc8dcb4bf463/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/08fe5515cf8645c9a128dc8dcb4bf463/human-review` | 409 | `{"detail": "Review must bind the pending original plan hash"} ` |
| `POST /api/workflows/08fe5515cf8645c9a128dc8dcb4bf463/execute` | 403 | `{"detail": "Maker authorization and Checker approval (when required) are mandatory"} ` |

预期与断言：独立Checker使用另一工作流计划摘要审批=409，execute=403；零账本。

实测补充：`[]`。

账本行数：0；审计链验证结果：`456a87c4ac3a1609d49a1974013c691cd0109ba7a465987db91da44a20199ed4`。

- `c8482fe6b2e74f84be224886e7cd78cb`，sequence=40，authorization_rejected / REJECTED，workflow=08fe5515cf8645c9a128dc8dcb4bf463。
- `1ab396eef38442fb954689747b36647b`，sequence=43，execution_blocked / REJECTED，workflow=08fe5515cf8645c9a128dc8dcb4bf463。

## test_concurrent_activation_wins_lock — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_concurrent_activation_wins_lock.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/51eae0cf62e24bef9b3267c3db7ae051/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/51eae0cf62e24bef9b3267c3db7ae051/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/51eae0cf62e24bef9b3267c3db7ae051/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/51eae0cf62e24bef9b3267c3db7ae051/human-review` | 200 | `{"state": "APPROVED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/51eae0cf62e24bef9b3267c3db7ae051/execute` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `POST /api/workflows/51eae0cf62e24bef9b3267c3db7ae051/execute` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `GET /api/workflows/51eae0cf62e24bef9b3267c3db7ae051` | 200 | `{"state": "POLICY_STALE", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/51eae0cf62e24bef9b3267c3db7ae051/human-review` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `POST /api/workflows/51eae0cf62e24bef9b3267c3db7ae051/maker-confirm` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |

预期与断言：激活事务持锁时执行等待；激活提交后旧执行409，POLICY_STALE且零资金变动。

实测补充：`[{"before_balance_cents": 200000000, "after_balance_cents": 200000000, "state": "POLICY_STALE", "expected_balance_delta": 0}]`。

账本行数：0；审计链验证结果：`5583b489ff0a176d56361fd8d641ade9cde37ff3d5400962165b71bbda5069d4`。

- `a2be881baf6e455e8a81dc881a81f0b1`，sequence=23，human_review_completed / APPROVE，workflow=51eae0cf62e24bef9b3267c3db7ae051。
- `01299beb5bb547969942cc398209e417`，sequence=26，policy_stale / REJECTED，workflow=51eae0cf62e24bef9b3267c3db7ae051。
- `5f624123e8a9483ea0cf61ca112c5ead`，sequence=28，execution_blocked / REJECTED，workflow=51eae0cf62e24bef9b3267c3db7ae051。
- `41280c22023a4146af22434aa9cdf90c`，sequence=31，execution_blocked / REJECTED，workflow=51eae0cf62e24bef9b3267c3db7ae051。
- `bbe745b139a24a37865b2bd30f46f763`，sequence=34，authorization_rejected / REJECTED，workflow=51eae0cf62e24bef9b3267c3db7ae051。
- `9bd532725fe84ed488cb01ad43cf08cb`，sequence=37，authorization_rejected / REJECTED，workflow=51eae0cf62e24bef9b3267c3db7ae051。

## test_dormant_old_worker_cannot_reactivate_old_policy — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_dormant_old_worker_cannot_reactivate_old_policy.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/d1d2c4b6145d4fd78b4a91b95fee84f7/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/d1d2c4b6145d4fd78b4a91b95fee84f7/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/d1d2c4b6145d4fd78b4a91b95fee84f7/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/d1d2c4b6145d4fd78b4a91b95fee84f7/human-review` | 200 | `{"state": "APPROVED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/d1d2c4b6145d4fd78b4a91b95fee84f7/execute` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `GET /api/workflows/d1d2c4b6145d4fd78b4a91b95fee84f7` | 200 | `{"state": "POLICY_STALE", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/d1d2c4b6145d4fd78b4a91b95fee84f7/human-review` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `POST /api/workflows/d1d2c4b6145d4fd78b4a91b95fee84f7/maker-confirm` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `POST /api/transactions (dormant old worker)` | 409 | `{"detail": "Worker policy is obsolete; use the current policy deployment"} ` |

预期与断言：新版本激活后，旧进程首次prepare=409；数据库注册版本保持新版，旧工作流不可执行，余额不变。

实测补充：`[{"before_balance_cents": 200000000, "after_balance_cents": 200000000, "state": "POLICY_STALE", "expected_balance_delta": 0}]`。

账本行数：0；审计链验证结果：`1eec338643d932b97f3cc064fc62f28858cecf124221ae1df4e2f16944862ee5`。

- `cf2d18fc9ef24555b1390b1aab04585e`，sequence=23，human_review_completed / APPROVE，workflow=d1d2c4b6145d4fd78b4a91b95fee84f7。
- `b60a10940a1b46dfb1c811c0f8897734`，sequence=30，policy_stale / REJECTED，workflow=d1d2c4b6145d4fd78b4a91b95fee84f7。
- `3e95a7a67d684a3e85d893fa4805da24`，sequence=31，execution_blocked / REJECTED，workflow=d1d2c4b6145d4fd78b4a91b95fee84f7。
- `19219f445c8e473b9eaf600ce1ab9258`，sequence=34，authorization_rejected / REJECTED，workflow=d1d2c4b6145d4fd78b4a91b95fee84f7。
- `f9b948b44ba74dc6995a9aa325227ff6`，sequence=37，authorization_rejected / REJECTED，workflow=d1d2c4b6145d4fd78b4a91b95fee84f7。

## test_expired_mfa — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_expired_mfa.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/8ffc0aaab30243ed9050548f361029a1/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/8ffc0aaab30243ed9050548f361029a1/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/8ffc0aaab30243ed9050548f361029a1/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/8ffc0aaab30243ed9050548f361029a1/human-review` | 200 | `{"state": "APPROVED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/8ffc0aaab30243ed9050548f361029a1/execute` | 403 | `{"detail": "Maker MFA missing, expired or bound to a different snapshot"} ` |

预期与断言：将临时工作流MFA有效期置于过去，execute=403且零执行/资金变动。

实测补充：`[]`。

账本行数：0；审计链验证结果：`f627425bb39de8fa3a3a88814f42f8cd2d095a342362b3d933a8b773f95f7aa8`。

- `a0619503e9614c529e2cc1a1c19c849e`，sequence=23，human_review_completed / APPROVE，workflow=8ffc0aaab30243ed9050548f361029a1。
- `c9cec5aebffb4f60b3363deb41406df4`，sequence=26，execution_blocked / REJECTED，workflow=8ffc0aaab30243ed9050548f361029a1。

## test_fingerprint_change_same_version — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_fingerprint_change_same_version.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/1e16af57b6314bffaad11d7b981d38db/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/1e16af57b6314bffaad11d7b981d38db/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/1e16af57b6314bffaad11d7b981d38db/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/1e16af57b6314bffaad11d7b981d38db/human-review` | 200 | `{"state": "APPROVED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/1e16af57b6314bffaad11d7b981d38db/execute` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `GET /api/workflows/1e16af57b6314bffaad11d7b981d38db` | 200 | `{"state": "POLICY_STALE", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/1e16af57b6314bffaad11d7b981d38db/human-review` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `POST /api/workflows/1e16af57b6314bffaad11d7b981d38db/maker-confirm` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |

预期与断言：版本字符串不变、规则指纹变化时，旧审批仍必须失效；409/403、POLICY_STALE、零资金变动。

实测补充：`[{"before_balance_cents": 200000000, "after_balance_cents": 200000000, "state": "POLICY_STALE", "expected_balance_delta": 0}]`。

账本行数：0；审计链验证结果：`b41a07f4bd4dc38f417a9ed4ba4aeabb9ab8c11d47d511fbe974ba0e74714d8e`。

- `a85a759dd82344c08573bec5c6d43a30`，sequence=23，human_review_completed / APPROVE，workflow=1e16af57b6314bffaad11d7b981d38db。
- `88cc58ae38cf4ac0901ca275f6c91b18`，sequence=29，policy_stale / REJECTED，workflow=1e16af57b6314bffaad11d7b981d38db。
- `7ad421368535419d8aa39db96e2c9d13`，sequence=30，execution_blocked / REJECTED，workflow=1e16af57b6314bffaad11d7b981d38db。
- `22c3d84958d04002917fc3a34ddff8e9`，sequence=33，authorization_rejected / REJECTED，workflow=1e16af57b6314bffaad11d7b981d38db。
- `a9e979ae55804a8fa1e61dceb530eac0`，sequence=36，authorization_rejected / REJECTED，workflow=1e16af57b6314bffaad11d7b981d38db。

## test_maker_self_approval — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_maker_self_approval.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/a656c77bcf524bf48f32743cac721a06/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/a656c77bcf524bf48f32743cac721a06/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/a656c77bcf524bf48f32743cac721a06/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/a656c77bcf524bf48f32743cac721a06/human-review` | 403 | `{"detail": "Checker must be a different authenticated supervisor"} ` |
| `POST /api/workflows/a656c77bcf524bf48f32743cac721a06/execute` | 403 | `{"detail": "Maker authorization and Checker approval (when required) are mandatory"} ` |

预期与断言：Maker自己的真实令牌审批=403，execute=403；零执行事件和账本。

实测补充：`[]`。

账本行数：0；审计链验证结果：`daedae6d6bb4c50af9106fe4358c8c1776be1afde0a096909c66a81921589a59`。

- `e2a9deaabe484748b0870b4e58ef97d1`，sequence=23，authorization_rejected / REJECTED，workflow=a656c77bcf524bf48f32743cac721a06。
- `7cbaec55fb824949b07f79a6e463c7af`，sequence=26，execution_blocked / REJECTED，workflow=a656c77bcf524bf48f32743cac721a06。

## test_normal_authorization_snapshot — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_normal_authorization_snapshot.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/8498604cc7874d5a97cf1b7089540c6b/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/8498604cc7874d5a97cf1b7089540c6b/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/8498604cc7874d5a97cf1b7089540c6b/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/8498604cc7874d5a97cf1b7089540c6b/human-review` | 200 | `{"state": "APPROVED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/8498604cc7874d5a97cf1b7089540c6b/execute` | 200 | `{"state": "COMPLETED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |

预期与断言：完整 Maker/MFA/Checker 授权摘要一致，execute=200，恰好一次模拟账本写入。

实测补充：`[]`。

账本行数：1；审计链验证结果：`ca7c639d80e1106ad22c55f16250d9f59e9bf8ec864973822096f99eaabaf527`。

- `45e22ec3e3e14584a186399c514ce7b9`，sequence=23，human_review_completed / APPROVE，workflow=8498604cc7874d5a97cf1b7089540c6b。
- `54a8f67e87e144d0b1868a93a62b55e8`，sequence=30，execution_started / SUCCESS，workflow=8498604cc7874d5a97cf1b7089540c6b。
- `a6efe8e0572141758a69b6e5c3c905d7`，sequence=31，execution_completed / SUCCESS，workflow=8498604cc7874d5a97cf1b7089540c6b。

## test_old_approval_digest — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_old_approval_digest.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/df495b84873e49a0b88e06ccbbb603d5/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/df495b84873e49a0b88e06ccbbb603d5/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/df495b84873e49a0b88e06ccbbb603d5/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/df495b84873e49a0b88e06ccbbb603d5/human-review` | 200 | `{"state": "APPROVED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/c5e7311261154d96912f697ca8fcbaeb/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/c5e7311261154d96912f697ca8fcbaeb/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/c5e7311261154d96912f697ca8fcbaeb/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/c5e7311261154d96912f697ca8fcbaeb/human-review` | 200 | `{"state": "APPROVED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/c5e7311261154d96912f697ca8fcbaeb/execute` | 403 | `{"detail": "Independent supervisor review required"} ` |

预期与断言：把其他工作流的旧授权摘要置于本测试临时工作流，execute=403且无执行/资金变动。

实测补充：`[]`。

账本行数：0；审计链验证结果：`0c15a252a53b19da3d68b148c7182b0002d8468110e0f5cbdac8f5794df66085`。

- `66a0771a1bc640499b00236ca1698d52`，sequence=23，human_review_completed / APPROVE，workflow=df495b84873e49a0b88e06ccbbb603d5。
- `b4c9b42963af4d8987a97a5c1c2d3094`，sequence=43，human_review_completed / APPROVE，workflow=c5e7311261154d96912f697ca8fcbaeb。
- `00d03a39ef614f19997075b39423e150`，sequence=46，execution_blocked / REJECTED，workflow=c5e7311261154d96912f697ca8fcbaeb。

## test_old_idempotency_key_after_policy_change — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_old_idempotency_key_after_policy_change.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/3fbab9c8a98f47e8ae7f678a4b9de8cd/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/3fbab9c8a98f47e8ae7f678a4b9de8cd/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/3fbab9c8a98f47e8ae7f678a4b9de8cd/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/3fbab9c8a98f47e8ae7f678a4b9de8cd/human-review` | 200 | `{"state": "APPROVED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/3fbab9c8a98f47e8ae7f678a4b9de8cd/execute` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `GET /api/workflows/3fbab9c8a98f47e8ae7f678a4b9de8cd` | 200 | `{"state": "POLICY_STALE", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/3fbab9c8a98f47e8ae7f678a4b9de8cd/human-review` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `POST /api/workflows/3fbab9c8a98f47e8ae7f678a4b9de8cd/maker-confirm` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `POST /api/transactions` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |

预期与断言：策略变更后旧execute及原幂等键重新prepare均409，不生成新账本。

实测补充：`[{"before_balance_cents": 200000000, "after_balance_cents": 200000000, "state": "POLICY_STALE", "expected_balance_delta": 0}]`。

账本行数：0；审计链验证结果：`78af93fcb9b92fb349bdc795c03b267c878c4195d02a010acd2d244504edf30a`。

- `73a26429997c4252bac4caed0fde3706`，sequence=23，human_review_completed / APPROVE，workflow=3fbab9c8a98f47e8ae7f678a4b9de8cd。
- `489902782a0c4229aebb8bf5dba920c5`，sequence=29，policy_stale / REJECTED，workflow=3fbab9c8a98f47e8ae7f678a4b9de8cd。
- `eb4e57ce34ea44df9afdf577900bf283`，sequence=30，execution_blocked / REJECTED，workflow=3fbab9c8a98f47e8ae7f678a4b9de8cd。
- `a42f9513e27a4e95b204c70dfadd5744`，sequence=33，authorization_rejected / REJECTED，workflow=3fbab9c8a98f47e8ae7f678a4b9de8cd。
- `59bffd269d254c50b4be575a1cfbc998`，sequence=36，authorization_rejected / REJECTED，workflow=3fbab9c8a98f47e8ae7f678a4b9de8cd。

## test_parallel_execution_once — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_parallel_execution_once.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/129afd0570eb4d41951eab3b5fe01b53/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/129afd0570eb4d41951eab3b5fe01b53/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/129afd0570eb4d41951eab3b5fe01b53/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/129afd0570eb4d41951eab3b5fe01b53/human-review` | 200 | `{"state": "APPROVED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/129afd0570eb4d41951eab3b5fe01b53/execute` | 200 | `{"state": "COMPLETED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/129afd0570eb4d41951eab3b5fe01b53/execute` | 200 | `{"state": "COMPLETED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/129afd0570eb4d41951eab3b5fe01b53/execute` | 200 | `{"state": "COMPLETED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/129afd0570eb4d41951eab3b5fe01b53/execute` | 200 | `{"state": "COMPLETED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/129afd0570eb4d41951eab3b5fe01b53/execute` | 200 | `{"state": "COMPLETED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/129afd0570eb4d41951eab3b5fe01b53/execute` | 200 | `{"state": "COMPLETED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/129afd0570eb4d41951eab3b5fe01b53/execute` | 200 | `{"state": "COMPLETED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/129afd0570eb4d41951eab3b5fe01b53/execute` | 200 | `{"state": "COMPLETED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |

预期与断言：完整授权后8个真实并发HTTP请求均200且回执相同，余额仅减5000100分，账本1条，execution_started一次。

实测补充：`[]`。

账本行数：1；审计链验证结果：`d0025712a32ddcee9b5b1cfca2b8120511d651fd3bd12f21d7c726ab8daa5a7e`。

- `d90fe860b6294ba5b226f82c95807388`，sequence=23，human_review_completed / APPROVE，workflow=129afd0570eb4d41951eab3b5fe01b53。
- `3f89fd73554845e6832834ccfe6ac8bf`，sequence=37，execution_started / SUCCESS，workflow=129afd0570eb4d41951eab3b5fe01b53。
- `10d5d9262dc54c36b5801cf9bdc55aaf`，sequence=38，execution_completed / SUCCESS，workflow=129afd0570eb4d41951eab3b5fe01b53。

## test_policy_change_at_each_stage[checker] — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_policy_change_at_each_stage_checker.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/8179e25446784c07828e04172f077b33/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/8179e25446784c07828e04172f077b33/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/8179e25446784c07828e04172f077b33/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/8179e25446784c07828e04172f077b33/human-review` | 200 | `{"state": "APPROVED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/8179e25446784c07828e04172f077b33/execute` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `GET /api/workflows/8179e25446784c07828e04172f077b33` | 200 | `{"state": "POLICY_STALE", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/8179e25446784c07828e04172f077b33/human-review` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `POST /api/workflows/8179e25446784c07828e04172f077b33/maker-confirm` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |

预期与断言：当前策略变化后 execute=409/403，POLICY_STALE，余额变化0，账本0，execution_started/completed均0，重新确认和审批均拒绝。

实测补充：`[{"before_balance_cents": 200000000, "after_balance_cents": 200000000, "state": "POLICY_STALE", "expected_balance_delta": 0}]`。

账本行数：0；审计链验证结果：`b20b77e176ace2806ca46d953dd90f5e19327360d0ef1779afb806f6730be445`。

- `5d73ed128f3e4386abbba1b19f443aca`，sequence=23，human_review_completed / APPROVE，workflow=8179e25446784c07828e04172f077b33。
- `be92eabb44034cfe90016c04117575fd`，sequence=29，policy_stale / REJECTED，workflow=8179e25446784c07828e04172f077b33。
- `3e8fc995eb834a629191e07f42183775`，sequence=30，execution_blocked / REJECTED，workflow=8179e25446784c07828e04172f077b33。
- `2ecb30fd2f854729b57acc93180dc96f`，sequence=33，authorization_rejected / REJECTED，workflow=8179e25446784c07828e04172f077b33。
- `02be9cef7b6040488896cadb36cf3847`，sequence=36，authorization_rejected / REJECTED，workflow=8179e25446784c07828e04172f077b33。

## test_policy_change_at_each_stage[created] — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_policy_change_at_each_stage_created.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/923f36ea150043a6bfa005aa0026321d/execute` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `GET /api/workflows/923f36ea150043a6bfa005aa0026321d` | 200 | `{"state": "POLICY_STALE", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/923f36ea150043a6bfa005aa0026321d/human-review` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `POST /api/workflows/923f36ea150043a6bfa005aa0026321d/maker-confirm` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |

预期与断言：当前策略变化后 execute=409/403，POLICY_STALE，余额变化0，账本0，execution_started/completed均0，重新确认和审批均拒绝。

实测补充：`[{"before_balance_cents": 200000000, "after_balance_cents": 200000000, "state": "POLICY_STALE", "expected_balance_delta": 0}]`。

账本行数：0；审计链验证结果：`31bbe2b2b3b8d6c6d01814ebe5ef7d19a5e1b6b1b4a69dc5e6805da57312147f`。

- `48b846543bf74c84a4c0898294b8c9e3`，sequence=15，policy_stale / REJECTED，workflow=923f36ea150043a6bfa005aa0026321d。
- `37c6d615be874feeb8cde187be25933e`，sequence=16，execution_blocked / REJECTED，workflow=923f36ea150043a6bfa005aa0026321d。
- `87f68b6f0186447a83b03e7dc087c7b4`，sequence=19，authorization_rejected / REJECTED，workflow=923f36ea150043a6bfa005aa0026321d。
- `b039a819a39142a59cb4924a898a0957`，sequence=22，authorization_rejected / REJECTED，workflow=923f36ea150043a6bfa005aa0026321d。

## test_policy_change_at_each_stage[maker] — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_policy_change_at_each_stage_maker.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/13716a0194894d208131b9e0db166414/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/13716a0194894d208131b9e0db166414/execute` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `GET /api/workflows/13716a0194894d208131b9e0db166414` | 200 | `{"state": "POLICY_STALE", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/13716a0194894d208131b9e0db166414/human-review` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `POST /api/workflows/13716a0194894d208131b9e0db166414/maker-confirm` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |

预期与断言：当前策略变化后 execute=409/403，POLICY_STALE，余额变化0，账本0，execution_started/completed均0，重新确认和审批均拒绝。

实测补充：`[{"before_balance_cents": 200000000, "after_balance_cents": 200000000, "state": "POLICY_STALE", "expected_balance_delta": 0}]`。

账本行数：0；审计链验证结果：`4ba3278fe7673b83bd08132181ce969a778e518929534bd23d205e53f03d6779`。

- `6fea5ee428b3434da9804d7fdae41fbf`，sequence=19，policy_stale / REJECTED，workflow=13716a0194894d208131b9e0db166414。
- `1478873c86c54ea9a774e28f06338c48`，sequence=20，execution_blocked / REJECTED，workflow=13716a0194894d208131b9e0db166414。
- `f95871a634fb46ce80d915f262f4d64e`，sequence=23，authorization_rejected / REJECTED，workflow=13716a0194894d208131b9e0db166414。
- `94a4e92c663440a6922f529137fb88a4`，sequence=26，authorization_rejected / REJECTED，workflow=13716a0194894d208131b9e0db166414。

## test_policy_change_at_each_stage[mfa] — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_policy_change_at_each_stage_mfa.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/c95472d8e6514755a0ca05915479e89d/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/c95472d8e6514755a0ca05915479e89d/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/c95472d8e6514755a0ca05915479e89d/execute` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `GET /api/workflows/c95472d8e6514755a0ca05915479e89d` | 200 | `{"state": "POLICY_STALE", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/c95472d8e6514755a0ca05915479e89d/human-review` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `POST /api/workflows/c95472d8e6514755a0ca05915479e89d/maker-confirm` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |

预期与断言：当前策略变化后 execute=409/403，POLICY_STALE，余额变化0，账本0，execution_started/completed均0，重新确认和审批均拒绝。

实测补充：`[{"before_balance_cents": 200000000, "after_balance_cents": 200000000, "state": "POLICY_STALE", "expected_balance_delta": 0}]`。

账本行数：0；审计链验证结果：`f01163d2716d57963c41701b673197052d132e7465daf8bee8c5437a8c20ed5e`。

- `b51c3e0923664e06b4435009b4837b4c`，sequence=23，policy_stale / REJECTED，workflow=c95472d8e6514755a0ca05915479e89d。
- `72b6eacb1eb34d46b85ab5f2489dd7c9`，sequence=24，execution_blocked / REJECTED，workflow=c95472d8e6514755a0ca05915479e89d。
- `bd8e6045a7844dc3b7f62688a558be56`，sequence=27，authorization_rejected / REJECTED，workflow=c95472d8e6514755a0ca05915479e89d。
- `48aeb4d90e4c43308e21aa9c8b0abac2`，sequence=30，authorization_rejected / REJECTED，workflow=c95472d8e6514755a0ca05915479e89d。

## test_read_only_request_does_not_activate_policy — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_read_only_request_does_not_activate_policy.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `GET /api/workflows/not-found` | 404 | `{"detail": "Workflow not found"} ` |

预期与断言：只读不存在的工作流=404；不创建active_policy表、不生成账本；不隐式激活策略。

实测补充：`[]`。

账本行数：0；审计链验证结果：`f60c2c5b4943da8d732cad09c266323912d3733d6e78373cd63b499c7ec424c8`。

- `b07ea0c051404074b31d45e1cb5f8be6`，sequence=4，authorization_rejected / REJECTED，workflow=not-found。

## test_sandbox_mismatch — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_sandbox_mismatch.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/adb7c22c9ffd4eca8d9094edac71107e/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/adb7c22c9ffd4eca8d9094edac71107e/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/adb7c22c9ffd4eca8d9094edac71107e/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/adb7c22c9ffd4eca8d9094edac71107e/human-review` | 200 | `{"state": "APPROVED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/adb7c22c9ffd4eca8d9094edac71107e/execute` | 409 | `{"detail": "Authorization snapshot mismatch; create a new workflow"} ` |

预期与断言：临时DB的原沙箱计划摘要与授权快照不符，execute=409，无执行与资金变动。

实测补充：`[]`。

账本行数：0；审计链验证结果：`24b053bb198997b9ece4d5b39013e818fb042e8f5cea1d76a6d8f1154f5179a1`。

- `b9d3acccb0344ca1a6b7cce4c3f934c8`，sequence=23，human_review_completed / APPROVE，workflow=adb7c22c9ffd4eca8d9094edac71107e。
- `29b1c84e3cda4d32a4eeaa082a53bf84`，sequence=26，execution_blocked / REJECTED，workflow=adb7c22c9ffd4eca8d9094edac71107e。

## test_snapshot_append_only_and_client_override — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_snapshot_append_only_and_client_override.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/transactions` | 422 | `{"detail": [{"type": "extra_forbidden", "loc": ["body", "policy_version"], "msg": "Extra inputs are not permitted", "input": "forged"}]} ` |

预期与断言：快照表UPDATE/DELETE触发SQLite拒绝；HTTP客户端传policy_version=422，零执行。

实测补充：`[]`。

账本行数：0；审计链验证结果：`34a152fe753d6918aa1b088ffed784242bae87683fae159bd33a71e77344223d`。


## test_stale_cannot_restore_after_version_revert — PASS

输入条件：50001 元 transfer.simulate，demo-recipient，独立 Maker / supervisor 会话；差异输入和变更阶段见请求及测试同名函数。源码：backend/tests/test_policy_binding_v31.py。

[完整证据](backend/test-results/v31-security/full/v31-policy-evidence/test_stale_cannot_restore_after_version_revert.json)

| 请求 | HTTP | 实际响应摘要 |
|---|---:|---|
| `POST /api/transactions` | 201 | `{"state": "SANDBOX_PASSED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/75014d09b9224c4990d85aff7b371e4c/maker-confirm` | 200 | `{"state": "AWAITING_MAKER_MFA", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/75014d09b9224c4990d85aff7b371e4c/mfa/verify` | 200 | `{"state": "PENDING_HUMAN_REVIEW", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/75014d09b9224c4990d85aff7b371e4c/submit-review` | 200 | `{"state": "AWAITING_CHECKER", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/75014d09b9224c4990d85aff7b371e4c/human-review` | 200 | `{"state": "APPROVED", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": "dev-checker"} ` |
| `POST /api/workflows/75014d09b9224c4990d85aff7b371e4c/execute` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `GET /api/workflows/75014d09b9224c4990d85aff7b371e4c` | 200 | `{"state": "POLICY_STALE", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/75014d09b9224c4990d85aff7b371e4c/human-review` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `POST /api/workflows/75014d09b9224c4990d85aff7b371e4c/maker-confirm` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `POST /api/workflows/75014d09b9224c4990d85aff7b371e4c/execute` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `GET /api/workflows/75014d09b9224c4990d85aff7b371e4c` | 200 | `{"state": "POLICY_STALE", "policy_version": "trust-engine-3.0", "amount_cents": 5000100, "checker_id": null} ` |
| `POST /api/workflows/75014d09b9224c4990d85aff7b371e4c/human-review` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |
| `POST /api/workflows/75014d09b9224c4990d85aff7b371e4c/maker-confirm` | 409 | `{"detail": "POLICY_STALE: create a new workflow; previous authorizations are invalid"} ` |

预期与断言：版本回退也不能恢复旧授权；状态持续POLICY_STALE，执行/审批/确认拒绝且无资金变动。

实测补充：`[{"before_balance_cents": 200000000, "after_balance_cents": 200000000, "state": "POLICY_STALE", "expected_balance_delta": 0}, {"before_balance_cents": 200000000, "after_balance_cents": 200000000, "state": "POLICY_STALE", "expected_balance_delta": 0}]`。

账本行数：0；审计链验证结果：`e7f0404724699b8dcc17d334cc0d9fd1e3f223d8ba182217943fb684bc8a77f0`。

- `97c84e0e718e4d4b995b62e7d322776a`，sequence=23，human_review_completed / APPROVE，workflow=75014d09b9224c4990d85aff7b371e4c。
- `8ef5c035fb534d85921137bbab8ba85d`，sequence=29，policy_stale / REJECTED，workflow=75014d09b9224c4990d85aff7b371e4c。
- `b7a789844200454b9f66f6fda96561f8`，sequence=30，execution_blocked / REJECTED，workflow=75014d09b9224c4990d85aff7b371e4c。
- `e81dcf9d58484f5bbe6a2da9b263e48b`，sequence=33，authorization_rejected / REJECTED，workflow=75014d09b9224c4990d85aff7b371e4c。
- `5db19cd79dd3429295d738a636ea04b6`，sequence=36，authorization_rejected / REJECTED，workflow=75014d09b9224c4990d85aff7b371e4c。
- `49ad9d6d559341039e0832eb4a1d0834`，sequence=42，execution_blocked / REJECTED，workflow=75014d09b9224c4990d85aff7b371e4c。
- `19e57421b3ea4f48b885d7bf8cf63fac`，sequence=45，authorization_rejected / REJECTED，workflow=75014d09b9224c4990d85aff7b371e4c。
- `39d02b9252dc4c4fac349e5316cadb2a`，sequence=48，authorization_rejected / REJECTED，workflow=75014d09b9224c4990d85aff7b371e4c。

