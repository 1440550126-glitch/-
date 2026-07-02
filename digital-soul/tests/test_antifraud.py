"""防诈骗测试。可直接运行：python tests/test_antifraud.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.antifraud import (  # noqa: E402
    is_fraud_question,
    kinds,
    scam_kind,
    smells_like_scam,
    tips,
    warn,
)


def test_impersonate_police():
    assert scam_kind("有个警官说我涉嫌洗钱，要把钱转到安全账户") == "冒充公检法"
    assert smells_like_scam("公安打电话来让我汇款配合资金清查")


def test_prize_scam():
    assert scam_kind("说我中了大奖，先交手续费才能领") == "中奖交税"


def test_health_product():
    assert scam_kind("讲座说这个保健品包治百病") == "保健神药"


def test_fake_child():
    assert scam_kind("妈我换号了，记一下，我出事了急用钱要打钱") == "冒充子女亲友"


def test_refund_scam():
    assert scam_kind("自称客服说快递理赔，让我下载软件做屏幕共享") == "退款客服"


def test_account_abnormal():
    assert scam_kind("银行说我账户异常，要我把短信验证码告诉他") == "账户异常"


def test_investment():
    assert scam_kind("有人带我刷单返利，说稳赚不赔") == "投资刷单"


def test_thaw_assets():
    assert scam_kind("民族资产解冻，交点善心钱就能分红") == "解冻资产"


def test_innocent_not_flagged():
    assert scam_kind("我儿子昨天换了个新发型") == ""
    assert scam_kind("今天天气不错，去银行取点钱") == ""
    assert not smells_like_scam("中午吃了红烧肉")


def test_warn_has_punch_reason_and_actions():
    w = warn(utterance="警官说我涉嫌洗钱要转到安全账户", name="老李")
    assert w.startswith("老李，打住！")
    assert "公检法" in w
    assert "不转账" in w and "96110" in w


def test_warn_unknown_empty():
    assert warn(utterance="今天星期几") == ""


def test_is_fraud_question():
    assert is_fraud_question("你看这是不是骗子")
    assert is_fraud_question("教我点反诈知识")
    assert not is_fraud_question("今天几号")


def test_kinds_and_tips():
    assert "冒充公检法" in kinds()
    assert any("96110" in t for t in tips())


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ antifraud: all tests passed")
