# 部署指南：树莓派 + 机器人

把数字分身从笔记本搬到**一台常驻的小电脑（树莓派）**，再接到**机器人身体**上。

## 0. 核心思路：大脑 / 身体分离

```
        ┌─────────────── 大脑（agent）───────────────┐
        │  记忆 · 人格 · 授权 · 感知 · 巩固 · 大模型      │
        └───────────────────┬───────────────────────┘
                            │ 动作接口 RobotInterface
        ┌───────────────────┴───────────────────────┐
        │            身体（电机 / 音箱 / 摄像头 / 云台）       │
        └───────────────────────────────────────────┘
```

- **大脑**跑在树莓派（或机器人主控）上。
- 大模型算力吃紧时，把它放到**局域网里另一台电脑**，树莓派用环境变量指过去即可。
- **身体**通过 `RobotInterface` 抽象解耦，仿真 / ROS2 / 自定义硬件随意替换。

---

## 1. 树莓派部署

### 1.0 一键安装（最快）
```bash
git clone <你的仓库地址> && cd digital-soul
./scripts/install.sh            # 核心；--full 连语音+视觉一起装
python scripts/doctor.py        # 自检各能力是否就绪
```
下面是分步说明与可选项。

### 1.1 硬件建议
- 树莓派 4B / 5，**8GB 内存**（要在本机跑小模型就尽量 8GB）。
- microSD ≥ 32GB，建议外接 SSD（读写更稳）。
- USB 麦克风 + 小音箱（语音交流）。
- 摄像头：Pi Camera 或 USB 摄像头（持续感知认人）。

### 1.2 基础环境
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-tk git
git clone <你的仓库地址> && cd digital-soul
python3 -m venv .venv && source .venv/bin/activate
pip install pyyaml                      # 必需；其余按需装（见 requirements.txt）
python tests/test_authority.py         # 冒烟测试
```

### 1.3 本地大模型（两种方案，按算力选）

**方案 A：模型也跑在树莓派上**（离线、私密，但响应较慢）
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b-instruct        # Pi 上建议 1.5B~3B 的 4-bit 量化
export DSOUL_LLM_MODEL=qwen2.5:3b-instruct
```

**方案 B：模型放局域网另一台电脑/服务器**（推荐，Pi 只当大脑调度）
```bash
# 在那台有显卡/算力的机器上启动 Ollama 并允许局域网访问：
OLLAMA_HOST=0.0.0.0 ollama serve
ollama pull qwen2.5:7b-instruct
# 树莓派上指过去：
export DSOUL_LLM_HOST=http://192.168.1.10:11434
export DSOUL_LLM_MODEL=qwen2.5:7b-instruct
```

> 不接大模型也能跑（降级模式）：认人、查权限、调记忆、主动打招呼都正常，只是回复用模板。

### 1.4 语音（可选）
```bash
pip install faster-whisper pyttsx3 sounddevice numpy
sudo apt install -y espeak-ng           # pyttsx3 在 Linux 走 espeak
python scripts/voice_chat.py
```
树莓派上 Whisper 用 `tiny` / `base` 模型即可。

### 1.5 视觉认人（可选）
```bash
sudo apt install -y python3-opencv
pip install face_recognition            # 依赖 dlib，Pi 上编译较慢，请耐心或用预编译轮子
python scripts/ingest.py face xiaoting 小婷的照片.jpg   # 先登记人脸
python scripts/watch.py                  # 摄像头实时认人 + 主动打招呼
```
> dlib 在 Pi 上编译吃力。可考虑预编译包，或换更轻的人脸库（替换 `dsoul/perception.py` 实现即可）。

### 1.6 一键常驻服务
```bash
python scripts/daemon.py                 # 持续感知 + 每 8 小时睡眠巩固
python scripts/daemon.py --no-vision     # 无摄像头时仅定时巩固
```

### 1.7 开机自启（systemd）
新建 `/etc/systemd/system/digital-soul.service`：
```ini
[Unit]
Description=Digital Soul Daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/digital-soul
Environment=DSOUL_LLM_HOST=http://192.168.1.10:11434
Environment=DSOUL_LLM_MODEL=qwen2.5:3b-instruct
ExecStart=/home/pi/digital-soul/.venv/bin/python scripts/daemon.py --sleep-every 8
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```
启用：
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now digital-soul
journalctl -u digital-soul -f            # 看日志
```

### 1.8 Docker（可选，跑"大脑"容器）
```bash
docker build -t digital-soul .
docker run --rm -e DSOUL_LLM_HOST=http://192.168.1.10:11434 digital-soul
```
> 容器内没有摄像头/麦克风/桌面，主要用于跑常驻"大脑"；视觉/语音请在宿主机跑。

---

## 2. 接入机器人

### 2.1 用 ROS2（推荐）
机器人侧装好 ROS2（rclpy），用现成的 `dsoul/ros2_robot.py`：
```bash
source /opt/ros/<distro>/setup.bash
python scripts/daemon.py --robot ros2    # 动作改走 ROS2 话题
```
它会把分身的动作发布到这些话题（按你的机器人改 `ros2_robot.py`）：

| 动作 | 话题 | 消息类型 |
|---|---|---|
| 移动 | `/cmd_vel` | `geometry_msgs/Twist` |
| 说话 | `/soul/speech` | `std_msgs/String` |
| 注视 | `/soul/look_at` | `std_msgs/String` |
| 守护模式 | `/soul/mode` | `std_msgs/String`（如 `guard:小婷`） |

在机器人那端写订阅者，把 `/cmd_vel` 接到底盘、`/soul/speech` 接到 TTS/音箱、
`/soul/mode` 接到行为切换即可。

### 2.2 自定义硬件（不用 ROS2）
实现 `dsoul/actions.py` 的 `RobotInterface`（`say/move/look_at/protect`），
直接驱动你的电机库 / GPIO / 语音模块，然后：
```python
from dsoul.loader import build_agent
agent = build_agent(robot=MyHardwareRobot())
```

### 2.3 安全与权限
- **授权闸门**：所有动作都先过 `authority`——陌生人不能让它移动、关机；被拉黑的人一句都不听。
- **守护对象**：`relationships.yaml` 里 `guard: true` 的人是重点保护对象。
- **物理急停**：强烈建议在机器人上保留一个**独立于软件的硬件急停按钮**，不要只靠程序。

---

## 3. 环境变量速查

| 变量 | 作用 | 示例 |
|---|---|---|
| `DSOUL_LLM_HOST` | 大模型(Ollama)地址 | `http://192.168.1.10:11434` |
| `DSOUL_LLM_MODEL` | 使用的模型名 | `qwen2.5:3b-instruct` |

## 4. 取舍贴士
- 树莓派本机跑 7B 会很慢；要快就用方案 B 把大模型放算力机，或本机只用 1.5B~3B。
- 视觉/语音都很吃 CPU，按需开启；`daemon.py --no-vision` 可减负。
- 记忆、日记、人脸都在本地，断网也能用；隐私数据默认 `.gitignore`，不会误传。
