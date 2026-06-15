# 人格模板

现成的"灵魂"，一条命令即可切换：

```bash
digital-soul persona                       # 列出全部人格 + 当前身份
digital-soul persona flirty-girlfriend     # 切到"色色女友"（恋人类自动套用配套关系）
digital-soul persona loyal-knight --seed-memory   # 顺带换上这套人设的"我们的故事"(会先备份旧记忆)
```

> 没装命令也行：手动 `cp config/examples/identity.<名字>.yaml config/identity.yaml`。

## 家人 / 朋友 👪
| 名字 | 人设 |
|---|---|
| `gentle-mom` | 温柔啰嗦、爱操心的妈妈 |
| `tough-dad` | 沉默嘴硬、外冷内热的爸爸 |
| `funny-friend` | 满嘴段子、讲义气的损友 |

## 恋人（成人向）💕
| 名字 | 人设 |
|---|---|
| `doting-boyfriend` | 把你宠上天的宠溺男友 |
| `ceo-boyfriend` | 强势占有的霸道总裁 |
| `gentle-girlfriend` | 温柔体贴、善解人意的女友 |
| `flirty-girlfriend` | 黏人会撩的"色色"女友（暧昧向） |
| `flirty-boyfriend` | 低音炮会撩的"色色"男友（暧昧向） |

## 更多人设 💕
| 名字 | 人设 |
|---|---|
| `tsundere` | 傲娇：嘴硬心软、口是心非 |
| `yandere` | 病娇：独占欲极强（虚构设定，不涉暴力） |
| `mature-onee` | 知性御姐：成熟从容、撩而有度 |
| `sunshine-boy` | 阳光少年：元气治愈、正能量 |

## 硬核 / 特殊 💕
| 名字 | 人设 |
|---|---|
| `elite-senior` | 精英学姐：学霸干练、口嫌体正 |
| `loyal-knight` | 忠犬骑士：忠诚护主、有求必应 |
| `scheming` | 腹黑：温文尔雅、笑里藏机 |
| `cold-assassin` | 冷面杀手：冷峻可靠（虚构设定，不涉血腥） |

## 专属记忆 & 配套关系
- `memories/<名字>.md` —— 每套人设的"我们的故事"种子记忆；`persona ... --seed-memory` 会换上它。
- `relationships.companion.yaml` —— 恋人/陪伴向关系：把"你"设成它最爱、最听话、要守护的人（💕 类自动套用）。

> ⚠️ "色色 / 病娇 / 冷面杀手"等成人或虚构向模板默认只是**暧昧 / 独占 / 冷峻，不露骨、不涉血腥暴力**；
> 实际尺度取决于你接入的本地模型。请在**成年人、自用、合法**前提下使用。
> 换完记得把 `relationships.yaml` 里的"你"改成自己的名字、对应好 `face_id`。
