# Codex 自动 curl 测试数据

本目录存放给 `自动测试.md` 使用的模拟数据。文件内容故意使用 `AUTO_*` 唯一关键词，便于 Codex 用 curl 上传知识库后，通过回答正文、流式 meta、会话 JSONL、daily memory、长期画像等记录判断链路是否完善。

## 文件说明

| 文件 | 用途 | 关键断言词 |
|---|---|---|
| `auto_phone_alpha.txt` | 产品咨询、产品规格、对比检索 | `AUTO Phone Alpha`、`AURORA-NPU`、`5120mAh`、`NebulaBlue` |
| `auto_phone_beta.txt` | 产品咨询、对比检索、未知对比边界 | `AUTO Phone Beta`、`IceBridge`、`6100mAh`、`120W` |
| `auto_troubleshoot.txt` | 故障排查检索 | `AUTO_SUPPORT_CHARGE_SLOW`、`AUTO_SUPPORT_WIFI_DROP` |
| `auto_after_sales_policy.txt` | 售后政策、拒绝编造测试 | `AUTO_POLICY_7D`、`AUTO_POLICY_WATER_DAMAGE` |
| `auto_memory_seed.md` | 记忆注入种子，可复制为 `data/memory/codex_auto_user/memory.md` | `偏好 AUTO Phone Alpha`、`预算 4500` |
| `auto_test_phone_alpha.svg` | 图片接口/图片数量限制测试用轻量文件 | `AUTO Phone Alpha` |

## 推荐上传顺序

1. `auto_phone_alpha.txt`
2. `auto_phone_beta.txt`
3. `auto_troubleshoot.txt`
4. `auto_after_sales_policy.txt`

