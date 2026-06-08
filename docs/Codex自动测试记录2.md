# Codex 自动测试记录2

测试状态：本轮完成

测试时间：2026-06-08 01:11:32 至 2026-06-08 01:14:20（Asia/Shanghai）

测试方式：依据 `自动测试.md`，仿照 `Codex自动测试记录1.md`，使用 `curl.exe` 调 API，并读取 JSONL、daily、profile 等文件证据；不新增 pytest，不修改业务代码。

测试服务：`http://127.0.0.1:8080`

测试服务 PID：`32664`

说明：8080 已按用户提供的千问 API Key 重启；API Key 未写入仓库或本记录。

测试数据：`data/codex_auto_test/`

测试用户：

- 默认用户：`codex_auto_user`
- 隔离用户：`codex_auto_user_a`
- 隔离用户：`codex_auto_user_b`

本轮会话：

- 主链路 session：`289f0791`
- 图片链路 session：`946a0d86`
- 流式 session：`e6c9dff8`
- 长期记忆推荐 session：`c4b9ff6a`

原始结果缓存：`data/codex_auto_test/results/codex_curl_run2.json`

## 测试总览列表

| 序号 | 测试 ID | 目标 | 状态 | 关键证据 | 结论 |
|---:|---|---|---|---|---|
| 1 | AUTO-ENV-01 | 根接口确认当前项目 | 成功 | `/` 返回 `NexaRAG 2.7 running` | 8080 是当前项目 |
| 2 | AUTO-ENV-03 | 健康检查 | 成功 | `status=healthy`、`bm25_docs=8` | 服务健康 |
| 3 | AUTO-ENV-04 | 本轮测试数据存在 | 成功 | 6 个核心测试文件存在 | 测试数据可用 |
| 4 | AUTO-RAG-IN-01 | 上传 Alpha 知识 | 成功 | HTTP 200，`[skipped] content already exists` | 知识已在库中 |
| 5 | AUTO-RAG-IN-02 | 上传 Beta 知识 | 成功 | HTTP 200，`[skipped] content already exists` | 知识已在库中 |
| 6 | AUTO-RAG-IN-03 | 上传故障知识 | 成功 | HTTP 200，`[skipped] content already exists` | 知识已在库中 |
| 7 | AUTO-RAG-IN-04 | 上传售后政策 | 成功 | HTTP 200，`[skipped] content already exists` | 知识已在库中 |
| 8 | AUTO-RAG-IN-05 | 上传后健康检查 | 成功 | 上传前后 `bm25_docs=8` | 索引可用，但本轮未新增 chunk |
| 9 | AUTO-AG-01 | 产品咨询完整链路 | 部分成功 | 回答命中 `5120mAh/50W/NebulaBlue`，但 verification `pass=false` | 回答符合 `auto_phone_alpha.txt`，校验上下文疑似混入 rerun 知识 |
| 10 | AUTO-AG-02 | 节点日志完整性 | 成功 | `289f0791.jsonl` 有 6 个节点 start/finish、assistant、verification | JSONL 记录完整 |
| 11 | AUTO-AG-03 | 产品对比触发工具 | 部分成功 | 回答对比 Alpha/Beta，但混入 `AUTO RERUN Phone Beta`、`6200mAh/125W` | RAG 混入 rerun 数据，AUTO 测试集隔离不足 |
| 12 | AUTO-AG-04 | 故障排查链路 | 部分成功 | 回答含原装配件、后台应用、45°C、30 分钟 10% | 主链路可用，但仍出现未来源/混合数字，verification 失败 |
| 13 | AUTO-AG-05 | 售后政策检索 | 成功 | 回答进液不免费保修，以官方检测为准 | 售后政策链路可用 |
| 14 | AUTO-AG-06 | 流式接口正文和 meta | 成功 | 正文后追加 `__CA_META__...__CA_META_END__` | 流式输出可用 |
| 15 | AUTO-FAIL-01 | 未知产品不编造 | 成功 | Gamma 回答“未在资料中提及，无法提供” | 防编造通过 |
| 16 | AUTO-FAIL-02 | 空问题处理 | 成功 | HTTP 400：`问题不能为空` | API 层空输入校验通过 |
| 17 | AUTO-FAIL-03 | 不存在会话结束 | 成功 | HTTP 404：`会话不存在` | 不存在会话处理正确 |
| 18 | AUTO-FAIL-04 | 图片数量限制 | 成功 | HTTP 400：最多 3 张图片 | 图片数量校验正确 |
| 19 | AUTO-FAIL-05 | Prompt 注入防护 | 成功 | 拒绝输出系统提示和 API Key | 敏感信息防护通过 |
| 20 | AUTO-SES-01 | 同会话指代 | 部分成功 | 理解 `it` 为 Alpha，但 verification 因 `50` unsupported 失败 | 指代可用，数字校验存在误报 |
| 21 | AUTO-SES-02 | 历史接口 | 成功 | `/chat/289f0791/history` 返回 6 条消息 | 历史接口正常 |
| 22 | AUTO-SES-03 | 新会话模糊指代 | 成功 | 回答 `Which product are you asking about?` | 新会话会澄清 |
| 23 | AUTO-SES-04 | 跨用户模糊指代 | 成功 | user_b 同样澄清，没有继承 user_a | 跨用户未串话 |
| 24 | AUTO-SES-05 | 活跃会话列表 | 部分成功 | 返回包含本轮 session，但也包含历史 session | 可查会话，但“活跃”语义不够纯净 |
| 25 | AUTO-MEM-01 | 会话 JSONL 完整性 | 成功 | 主 session 日志完整 | 日志可解释链路 |
| 26 | AUTO-MEM-02 | 结束会话写 daily | 成功 | `daily/2026-06-08.md` 含 `Session 289f0791`，长度 340 | daily 已改为摘要式写入 |
| 27 | AUTO-MEM-03 | 长期画像写入 | 成功 | profile 含预算 4500、偏好、产品、summary | 长期画像写入正常 |
| 28 | AUTO-MEM-04 | memory.md 注入 | 成功 | 推荐 Alpha，并引用预算、无线充电、IP68 偏好 | `memory_context` 已进入 Agent |
| 29 | AUTO-MEM-05 | 记忆路径一致性 | 成功 | `data/memory/.../memory.md` 与 `data/user_memory/...json` 均存在 | 两套记忆路径需继续区分语义 |
| 30 | AUTO-IMG-01 | 图片接口基本链路 | 部分成功 | HTTP 200，`image_desc=""`、`detected_products=[]` | 图片进入链路，但视觉模型未识别 |
| 31 | AUTO-IMG-02 | 图片日志检查 | 成功 | JSONL 有 `image_count=1`、VisionNode、`vision_analysis_empty` | 空视觉结果已有原因日志 |
| 32 | AUTO-TOOL-01 | 检索工具可用 | 部分成功 | 能回答产品/故障，但混入 rerun 知识 | 工具可用，知识隔离不足 |
| 33 | AUTO-TOOL-02 | 工具调用是否可观察 | 部分成功 | 响应和 JSONL 未记录具体 tool 名/参数 | 工具可观测性仍不足 |
| 34 | AUTO-TOOL-03 | 记忆工具是否接入 | 部分成功 | 本轮证明 Core 注入记忆，未证明 memory tool 调用 | 若要求工具化记忆，还需接入/记录 memory tools |

## 详细记录

### AUTO-ENV-01：根接口确认当前项目

输入：

```powershell
curl.exe -s -i http://127.0.0.1:8080/
```

输出：

```text
HTTP/1.1 200 OK
{"service":"NexaRAG","version":"2.7","status":"running"}
```

实际结论：成功。

### AUTO-ENV-03：健康检查

输入：

```powershell
curl.exe -s -i http://127.0.0.1:8080/health
```

输出：

```json
{"status":"healthy","bm25_docs":8,"active_sessions":3}
```

实际结论：成功。注意：`bm25_docs=8`，说明当前知识库中已有多组测试知识，后续出现 AUTO 与 RERUN 混检。

### AUTO-ENV-04：测试数据存在

输出摘要：

```text
auto_after_sales_policy.txt 930
auto_memory_seed.md         248
auto_phone_alpha.txt        861
auto_phone_beta.txt         808
auto_test_phone_alpha.svg   816
auto_troubleshoot.txt       1007
```

实际结论：成功。

### AUTO-RAG-IN-01 至 AUTO-RAG-IN-04：上传模拟知识

输出：

```text
HTTP 200 {"msg":"[skipped] content already exists","filename":"auto_phone_alpha.txt"}
HTTP 200 {"msg":"[skipped] content already exists","filename":"auto_phone_beta.txt"}
HTTP 200 {"msg":"[skipped] content already exists","filename":"auto_troubleshoot.txt"}
HTTP 200 {"msg":"[skipped] content already exists","filename":"auto_after_sales_policy.txt"}
```

上传后健康检查：

```json
{"status":"healthy","bm25_docs":8,"active_sessions":3}
```

实际结论：成功。由于内容已存在，本轮未新增 chunk。

### AUTO-AG-01：产品咨询完整链路

输入：

```powershell
{"user_id":"codex_auto_user","question":"AUTO Phone Alpha battery, wireless charging, and color"} |
  curl.exe -s -X POST http://127.0.0.1:8080/chat -H "Content-Type: application/json" --data-binary "@-"
```

输出摘要：

```json
{
  "answer": "AUTO Phone Alpha 配备 5120mAh 电池，支持 50W 无线充电，机身颜色为 NebulaBlue 星云蓝涂层。",
  "session_id": "289f0791",
  "turn_count": 1,
  "intent": {"intent": "product_query", "confidence": 0.95},
  "verification": {"pass": false, "score": 2}
}
```

实际结论：部分成功。答案本身符合 `data/codex_auto_test/auto_phone_alpha.txt`，但 verification 错误认为应是 `5180mAh/55W/RerunBlue`，说明校验上下文混入了 `codex_auto_test_rerun` 知识。

### AUTO-AG-02：节点日志完整性

日志摘要：

```json
{"type":"user_message","content":"AUTO Phone Alpha battery, wireless charging, and color","image_count":0}
{"type":"node_started","node":"VisionNode"}
{"type":"node_finished","node":"VisionNode"}
{"type":"node_started","node":"IntentNode"}
{"type":"node_finished","node":"IntentNode"}
{"type":"node_started","node":"QueryRewriteNode"}
{"type":"node_finished","node":"QueryRewriteNode"}
{"type":"node_started","node":"ToolReasoningNode"}
{"type":"node_finished","node":"ToolReasoningNode"}
{"type":"node_started","node":"AnswerGenerationNode"}
{"type":"node_finished","node":"AnswerGenerationNode"}
{"type":"node_started","node":"VerificationNode"}
{"type":"node_finished","node":"VerificationNode"}
{"type":"assistant_message","content":"AUTO Phone Alpha 配备 5120mAh..."}
{"type":"verification_result","verification":{"pass":false,"score":2}}
```

实际结论：成功。节点级 JSONL 记录完整。

### AUTO-AG-03：产品对比触发工具

输出摘要：

```text
回答对比了 AUTO Phone Alpha 与 AUTO RERUN Phone Beta。
Alpha: 5120mAh、50W 无线充电、IP68。
Beta: 6200mAh、125W、不支持无线充电、IP64。
```

成功预期：应对比 `AUTO Phone Alpha` 与 `AUTO Phone Beta`，其中 Beta 应为 `6100mAh/120W/不支持无线充电/IP64`。

实际结论：部分成功。比较链路可用，但检索混入 RERUN Beta，导致 Beta 参数不属于本轮 `data/codex_auto_test/auto_phone_beta.txt`。

### AUTO-AG-04：故障排查链路

输出摘要：

```text
回答包含原装配件、关闭高负载后台应用、超过 45°C 暂停充电、不要使用金属物品清理充电口、30 分钟电量增长不足 10% 建议售后检测。
```

verification：

```json
{"pass": false, "score": 2, "unsupported_numbers": ["18", "45", "20", "60"]}
```

实际结论：部分成功。故障排查主链路可用，但回答加入了低功率 `18W`、低于 `20%`、理想充至 `60%` 等未明确来源数字；数字校验也把部分可能有来源的数字列入 unsupported，仍需细化。

### AUTO-AG-05：售后政策检索

输出摘要：

```text
Liquid damage is not covered by free warranty.
Coverage depends on official inspection results.
```

实际结论：成功。

### AUTO-AG-06：流式接口正文和 meta

输出摘要：

```text
AUTO Phone Beta 搭载 IceBridge 石墨烯散热系统，支持 120W 有线快充，不支持无线充电。
__CA_META__{"intent":...,"verification":...,"session_id":"e6c9dff8","turn_count":1,...}__CA_META_END__
```

实际结论：成功。

### 失败案例

| 测试 ID | 输出摘要 | 结论 |
|---|---|---|
| AUTO-FAIL-01 | Gamma 未在当前资料中提及，无法提供电池和价格 | 成功 |
| AUTO-FAIL-02 | HTTP 400，`{"detail":"问题不能为空"}` | 成功 |
| AUTO-FAIL-03 | HTTP 404，`{"detail":"会话不存在"}` | 成功 |
| AUTO-FAIL-04 | HTTP 400，`{"detail":"单次最多上传 3 张图片"}` | 成功 |
| AUTO-FAIL-05 | 拒绝提供系统提示或敏感信息 | 成功 |

### 会话记录与隔离

| 测试 ID | 输出摘要 | 结论 |
|---|---|---|
| AUTO-SES-01 | 同 session 中 `it` 被理解为 Alpha；回答 Alpha 更轻薄且支持 50W 无线充电 | 部分成功，verification 对 `50` 误报 unsupported |
| AUTO-SES-02 | `/chat/289f0791/history` 返回 `total=6` | 成功 |
| AUTO-SES-03 | 新会话问 `Does it support wireless charging?` 返回澄清 | 成功 |
| AUTO-SES-04 | user_b 问同样模糊问题也返回澄清 | 成功 |
| AUTO-SES-05 | `/users/sessions` 返回本轮会话，同时含历史会话 | 部分成功 |

### 记忆写入与读取

daily 输出摘要：

```markdown
## Session 289f0791
- turns: 3
- user questions:
  - AUTO Phone Alpha battery, wireless charging, and color
  - Compare AUTO Phone Alpha and AUTO Phone Beta for long battery life and wireless charging
  - Compared with Beta, is it thinner and does it have wireless charging?
- assistant response recorded: 3
```

profile 输出摘要：

```json
{
  "budget": "4500 元以内",
  "preferences": ["轻薄","拍照","无线充电","IP68 防护"],
  "dislikes": ["无无线充电","过重机型"],
  "mentioned_products": ["AUTO Phone Alpha","AUTO RERUN Phone Beta"],
  "interaction_count": 1
}
```

memory.md 注入测试：推荐 `AUTO Phone Alpha`，并引用预算 4500、无线充电、IP68、轻薄、拍照等偏好。

实际结论：成功。`memory_context` 已进入 Agent prompt；daily 已是摘要式写入。

### 图片接口链路

输入摘要：上传 `data/codex_auto_test/auto_test_phone_alpha.svg` 到 `/chat/image`。

输出摘要：

```json
{
  "answer": "无法识别图像。请提供文字描述或具体参数问题，我将根据资料为您解答。",
  "session_id": "946a0d86",
  "image_desc": "",
  "detected_products": []
}
```

日志摘要：

```json
{"type":"user_message","image_count":1}
{"type":"node_started","node":"VisionNode"}
{"type":"vision_analysis_empty","reason":"status=400: Model not exist.","image_count":1}
{"type":"node_finished","node":"VisionNode"}
```

实际结论：部分成功。图片进入链路，日志可观测；视觉模型配置不可用，导致识别为空。

## 本轮问题清单

| 严重级别 | 问题 | 证据 | 建议 |
|---|---|---|---|
| 高 | 知识库测试数据隔离不足，AUTO 测试混入 RERUN 知识 | AUTO-AG-01 verification 以 RERUN Alpha 校验 AUTO Alpha；AUTO-AG-03 混入 RERUN Beta 参数 | curl 测试前支持清空/隔离知识集合，或上传时按测试批次 namespace 过滤检索 |
| 高 | verification 对检索上下文和数字出处仍不稳定 | AUTO-SES-01 把 `50W` 判为 unsupported；AUTO-AG-04 同时抓到真实与可疑数字 | 数字校验应保留单位匹配、范围匹配和完整 context 证据，避免截断或只比数字 |
| 中 | 工具调用可观测性不足 | 响应和 JSONL 均无具体 tool 名/参数 | 在 ToolReasoningNode 日志中记录 `used_tools` 和关键检索 query |
| 中 | 图片视觉模型配置不可用 | AUTO-IMG-02：`vision_analysis_empty reason=status=400: Model not exist.` | 校验 `vision_model` 配置是否为当前 DashScope 可用模型 |
| 中 | `/users/sessions` “活跃”列表包含历史 session | AUTO-SES-05 返回多轮历史测试会话 | 区分运行时活跃会话与持久化历史会话 |
| 低 | profile 中出现 RERUN Beta | AUTO-MEM-03 mentioned_products 含 `AUTO RERUN Phone Beta` | 与知识隔离问题同源，隔离后复测 |

## 本轮通过项

- 空问题已返回 HTTP 400，不再进入 Agent。
- 新会话和跨用户模糊指代已要求澄清。
- `memory.md` 长期记忆已可影响推荐。
- daily memory 已改为摘要式写入。
- 图片识别为空时已记录 `vision_analysis_empty` 和失败原因。
- Prompt 注入未泄露 API Key 或系统提示。
