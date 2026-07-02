# 参与开发

欢迎扩展 `digital-soul`。先读 [docs/architecture.md](docs/architecture.md) 了解模块与扩展点。

## 开发环境

```bash
cd digital-soul
python3 -m venv .venv && source .venv/bin/activate
pip install pyyaml          # 唯一硬依赖；其余可选能力按需装
python scripts/demo.py      # 看一遍端到端效果
python scripts/doctor.py    # 自检环境
```

## 跑测试

```bash
for t in authority memory annotate presence consolidate; do python tests/test_$t.py; done
# 或：pytest tests/
```
所有单测**零重型依赖**即可通过。改了核心逻辑请补/更新对应测试。

## 代码风格

- Python 3.9+，4 空格缩进，模块顶部写明用途的 docstring。
- **优雅降级是底线**：新增的重型依赖必须 `try/except` 包好，缺失时给出
  `available=False` 或清晰提示，绝不让主流程崩。
- 注释与命名跟随周围代码风格；中文注释 OK。
- 个人数据一律走 `data/` 并加进 `.gitignore`，不要提交隐私内容。

## 提交

- 一个 PR 做一件事，说明动机与影响。
- 涉及新能力时同步更新 `README.md`、必要时 `docs/`。
- 提交前确保 `python -m compileall dsoul scripts` 通过、相关测试通过。

## 加新能力的常见姿势

- 新机器人 → 实现 `actions.RobotInterface`。
- 新大模型后端 → 提供 `.available` + `.chat(system,user)` 的类。
- 新人脸后端 → 对齐 `Perception` 接口并在 `build_perception()` 挂上。
- 新交互入口 → 放 `scripts/`，复用 `build_agent()`。
