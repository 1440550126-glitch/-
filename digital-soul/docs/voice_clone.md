# 给数字分身一把"本人的嗓音"——开源声音大模型选型与接入

> 你问的"有没有开源的声音大模型"——有，而且不少都能**离线本地**跑，
> 用一小段录音就把 TA 说话的声音"克隆"出来，让分身不只是会打字，
> 而是用**那个熟悉的声音**跟你说话。下面是 2025–2026 这一年里，
> 中文场景最值得用的几个，以及怎么接到本项目里。

本项目**不强制**任何一个：不接，照样能用系统自带的 `say`/`espeak` 出声（零安装）；
接上克隆模型，就成了"本人的声线"。接入点只有一个——
`config/identity.yaml` 里的 `voice.tts_cmd`（见文末"接入"一节）。

---

## 一、开源声音大模型横评（按中文克隆体验排序）

### 1. GPT-SoVITS ⭐ 中文克隆首选
- **一句话**：1 分钟素材就能克隆音色，5 秒素材也能做零样本；中文/粤语/日英韩都支持，社区最活跃，整合包开箱即用。
- **适合**：用长辈/亲人留下的一小段语音，克隆出最像本人的中文声线。
- **门槛**：有显卡最舒服（CPU 也能跑，慢一些）；Windows 整合包双击即用，Mac/Linux 按仓库说明装。
- **仓库**：GitHub `RVC-Boss/GPT-SoVITS`

### 2. CosyVoice 2 / CosyVoice 3 ⭐ 阿里出品，工程稳
- **一句话**：阿里通义团队的流式 TTS，零样本音色克隆、跨语种、情感与方言都不错；CosyVoice 2 是当前稳定版，CosyVoice 3 进一步提了自然度。
- **适合**：想要稳定、可流式、长文本不破音的中文播报。
- **门槛**：提供 Python SDK 与命令行；建议有 GPU。
- **仓库**：GitHub `FunAudioLLM/CosyVoice`

### 3. Fish Speech V1.5 / OpenAudio
- **一句话**：多语种零样本克隆，延迟低、自然度高，英文 TTS 评测里名列前茅，中文也好用；开源可商用许可较友好。
- **适合**：想要一个综合素质高、部署文档完善的多语种引擎。
- **仓库**：GitHub `fishaudio/fish-speech`

### 4. IndexTTS-2
- **一句话**：B 站系开源 TTS，主打"可控时长 + 情感表达"的零样本克隆，中文表现亮眼。
- **适合**：想让克隆嗓音带点情绪起伏（高兴/难过/叮嘱），而不是平板朗读。
- **仓库**：GitHub `index-tts/index-tts`

### 5. Chatterbox（Resemble AI）
- **一句话**：开源、主打"超过 ElevenLabs 的自然度"，带情感夸张度调节；以英文为主，中文要看版本支持。
- **适合**：英文为主、想要表现力的场景。
- **仓库**：GitHub `resemble-ai/chatterbox`

### 6. Kokoro（82M，小而快）
- **一句话**：超轻量（8200 万参数），CPU 也能实时；但用的是**固定预置音色**，**不做**任意音色克隆。
- **适合**：只想要一个又快又稳的播报嗓子，不需要"克隆某个人"。
- **仓库**：HuggingFace `hexgrad/Kokoro-82M`

> **怎么选？**
> - 想"复刻那个人的中文声音" → **GPT-SoVITS**（素材少、最像）或 **CosyVoice 2**（最稳）。
> - 想要"高素质多语种、文档全" → **Fish Speech**。
> - 想要"带情绪的克隆" → **IndexTTS-2**。
> - 只要"一个快嗓子、不克隆" → **Kokoro**。

---

## 二、给"复刻亲人声音"的推荐路线

1. **收集素材**：找一段 TA 清晰说话的录音，**安静、单人、30 秒～几分钟**最好（GPT-SoVITS 1 分钟即可起步，5 秒也能零样本）。去掉背景音乐/杂音。
2. **跑一个模型**：先用 **GPT-SoVITS 整合包**最省心；追求稳定可换 **CosyVoice 2**。
3. **导出一个"念一句话"的命令**：把模型包装成「输入文字 → 合成 wav → 播放」的一条命令（下面给了现成的包装脚本）。
4. **填进配置**：把这条命令写到 `config/identity.yaml` 的 `voice.tts_cmd`，分身从此用本人嗓音说话。

> ⚠️ **一句提醒**：克隆的是**你有权使用**的声音（你自己、或在世亲人同意、或家人留下的纪念素材）。
> 别拿它去冒充他人、行骗或骚扰——给思念一个寄托，不给坏事开方便之门。

---

## 三、接入本项目 —— 三步"调通"

分身播报的优先级是：
**`voice.tts_cmd`（外部克隆嗓音，最像本人）> `pyttsx3` > 系统自带 `say`/`espeak` > 打印文字。**

### 第 0 步：先体检（看看缺啥）

```bash
python scripts/voice_doctor.py
```

它会一条条告诉你：能不能听、能不能说、播放器有没有、克隆命令接没接通，
**没装的直接给出补救命令**，最后还会用当前嗓音真念一句听个响。

### 第 1 步：先让它「能出声」（零克隆，先听个响）

- **Mac**：自带 `say` 和 `afplay`，啥都不用装，`voice_doctor` 直接就念了。
  想要中文女声：系统设置→辅助功能→朗读内容→下载「Tingting」，再把 `voice.voice` 填 `Tingting`。
- **Linux**：`sudo apt install espeak-ng alsa-utils`（说 + 放）。
- 跑 `python scripts/voice_chat.py`，对话回应就出声了，还会边说边动。

### 第 2 步：换成「本人的声线」（接克隆模型）

1. 找一段本人清晰说话的录音（30 秒以上最好，安静、单人），放到 `voices/mom.wav`。
2. 把 GPT-SoVITS 跑起来（整合包最省心，详见上文），起它自带的 HTTP 服务 `api.py`。
3. 在 `config/identity.yaml` 填 `voice.tts_cmd`（**`{text}` 写裸的就行，程序自动安全转义**；
   也可用环境变量 `$DSOUL_TEXT` 取原文）：

```yaml
voice:
  rate: 185
  volume: 0.95
  voice: ""
  # A) 推荐：用自带包装脚本（已处理「合成 wav → 播放」、URL 编码、找不到引擎自动回落系统嗓音）
  tts_cmd: "python scripts/say_clone.py --engine gpt-sovits --ref voices/mom.wav {text}"

  # B) CosyVoice / 自己的 CLI（你包好一个「输入文字→合成→播放」的命令）
  # tts_cmd: "python -m my_cosyvoice --prompt voices/dad.wav --out /tmp/s.wav --text {text} && (afplay /tmp/s.wav || aplay /tmp/s.wav)"
```

> ⚠️ 直接拿 `curl` 拼 URL 调 HTTP 接口的，**别在 `{text}` 外面再套引号**——`{text}` 会被自动 shell 转义，
> 而且 URL 还需要单独编码。要走 HTTP，建议用上面的 `say_clone.py`（它已经做了 URL 编码）。

4. 再体检一次 `python scripts/voice_doctor.py`：克隆那一行变 ✅，并念出本人嗓音，就通了。

### 第 3 步：日常用起来

```bash
python scripts/voice_chat.py        # 语音对话，回应用本人嗓音、且边说边动、带情绪
python scripts/daemon.py --voice    # 常驻：主动问候/守护提醒也用本人嗓音
```

**接不通也绝不哑**：克隆命令出错（服务没起/没装/打错），会自动回落到系统 `say`/`espeak`，
日子照过，回头再调。

---

## 四、自带包装脚本 `scripts/say_clone.py`

我们附了一个**模型无关**的薄包装：它把"合成 → 播放"这件事统一好，
你只要在里面把对应引擎那几行换成你本地的调用即可（脚本里有标注 `# TODO 接你的模型`）。
默认它会优雅降级——引擎没接好时，回落到系统 `say`/`espeak`，**绝不让分身突然哑掉**。

```bash
# 单测（纯逻辑，不需要真模型）：
python tests/test_say_clone.py

# 手动念一句（没接真引擎时会用系统嗓音兜底）：
python scripts/say_clone.py --engine system "你回来啦，外面冷不冷？"
```

---

## 参考来源

- SiliconFlow《Best Open Source Models for Voice Cloning》
  https://www.siliconflow.com/articles/en/best-open-source-models-for-voice-cloning
- Resemble AI《Best Open-Source AI Voice Cloning Tools》
  https://www.resemble.ai/resources/best-open-source-ai-voice-cloning-tools
- bymar《Open-Source Voice Cloning Alternatives to ElevenLabs (2026)》
  https://blog.bymar.co/posts/open-source-voice-cloning-alternatives-elevenlabs-2026/
- FindSkill《Best Open Source TTS 2026》
  https://findskill.ai/blog/best-open-source-tts-2026/
- IndexTTS-2 论文 https://arxiv.org/pdf/2505.17589
- GPT-SoVITS https://github.com/RVC-Boss/GPT-SoVITS ｜
  CosyVoice https://github.com/FunAudioLLM/CosyVoice ｜
  Fish-Speech https://github.com/fishaudio/fish-speech
