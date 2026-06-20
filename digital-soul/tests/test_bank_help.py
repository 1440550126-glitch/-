"""银行办事帮手测试。可直接运行：python tests/test_bank_help.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.bank_help import (  # noqa: E402
    count, find_topic, how_to, is_bank_query, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("ATM取钱", "银行卡挂失", "转账汇款", "忘记密码", "社保医保卡"):
        assert k in ts
    assert count() >= 6


def test_find_topic_alias():
    assert find_topic("ATM怎么取款") == "ATM取钱"
    assert find_topic("银行卡丢了咋办") == "银行卡挂失"
    assert find_topic("怎么汇款") == "转账汇款"
    assert find_topic("今天天气好") is None


def test_how_to_has_steps_and_tip():
    s = how_to("ATM取钱")
    assert "密码" in s and "先取卡" in s and "叮嘱" in s
    assert how_to("不存在") == ""


def test_transfer_has_strong_antiscam():
    s = how_to("转账")
    assert "骗子" in s and ("挂电话" in s or "核实" in s)     # 转账重点防骗
    assert "公检法" in s or "退款" in s


def test_password_reset_warns():
    s = how_to("忘记密码")
    assert "柜台" in s and ("验证码" in s or "骗子" in s)     # 改密码只能本人去柜台


def test_is_query_gating():
    assert is_bank_query("ATM怎么取钱")
    assert is_bank_query("银行卡丢了怎么挂失")
    assert is_bank_query("社保卡怎么用")
    assert not is_bank_query("今天天气好")
    assert not is_bank_query("我去了趟银行")                # 陈述、没问怎么办 → 不抢


def test_config_extra_topic():
    cfg = {"bank_help": {"topics": {"开通手机银行": ["带身份证和卡去柜台或自助开通", "别让陌生人帮你弄"]}}}
    assert "开通手机银行" in topics(cfg)
    assert how_to("开通手机银行", cfg).startswith("开通手机银行：")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ bank_help: all tests passed")
