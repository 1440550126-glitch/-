---
name: summarize-url
description: 抓取一个网页并产出结构化摘要（要点 + 关键结论）
when_to_use: 用户给出 http(s) 链接并希望总结、提炼、看看讲了什么
---

# 网页摘要

1. 调用 `web_fetch` 抓取用户给出的 URL（只支持 http/https）。
2. 基于正文产出：
   - 一句话主旨
   - 3–6 条关键要点
   - 对用户可能有用的结论 / 行动建议
3. 若内容与用户已知偏好相关，调用 `remember` 记下一条高价值信息（importance=4）。
4. 抓取失败时如实说明，不要臆造内容。
