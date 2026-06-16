"""多模型路由测试（离线，打桩请求）。python tests/test_llm.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.llm import LLM, LLMRouter, build_router  # noqa: E402


class _Cap(LLM):
    """跳过网络 ping、记录请求、回假数据。"""

    def _ping(self):
        return True

    def _post(self, path, payload):
        self.calls = getattr(self, "calls", [])
        self.calls.append((path, payload))
        if "completions" in path:
            return {"choices": [{"message": {"content": "好的"}}]}
        return {"message": {"content": "好的"}}


def test_ollama_chat_shape():
    m = _Cap(provider="ollama", model="qwen")
    assert m.chat("s", "u") == "好的"
    assert m.calls[-1][0] == "/api/chat" and m.calls[-1][1]["model"] == "qwen"


def test_openai_compatible_chat_shape():
    m = _Cap(provider="openai", host="http://x/v1", model="local")
    assert m.chat("s", "u") == "好的"
    assert m.calls[-1][0] == "/chat/completions"


def test_unreachable_is_unavailable():
    assert LLM(host="http://127.0.0.1:1", provider="ollama").available is False   # 没服务 → 降级


def test_router_for_task_and_panel():
    r = build_router({"default": {"model": "a"},
                      "tasks": {"reflect": {"model": "b"}},
                      "panel": [{"model": "c"}, {"model": "d"}]})
    assert r.default.model == "a"
    assert r.for_task("reflect").model == "b"
    assert r.for_task("不存在").model == "a"          # 回退默认
    assert [m.model for m in r.panel()] == ["c", "d"]


def test_router_direct():
    d, t = object(), object()
    r = LLMRouter(d, {"reflect": t})
    assert r.for_task("reflect") is t and r.for_task("x") is d


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ llm: all tests passed")
