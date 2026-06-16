"""跨设备记忆同步：把 ~/.mnemo 打包导出/导入，支持口令加密。

加密为纯标准库实现（PBKDF2-HMAC-SHA256 派生密钥 + SHA256 计数器流加密 + HMAC 完整性，
encrypt-then-MAC）。这不是 AES，但在零依赖前提下提供口令保护与防篡改；
对高度敏感数据，建议叠加系统级加密或换用经审计的加密库。
"""
from __future__ import annotations

import hashlib
import hmac
import io
import os
import tarfile
from pathlib import Path

MAGIC = b"MNEMOSYNC1"
# 同步内容：记忆库 / 配置 / 技能 / 插件（排除审计、轨迹、pid 等运行态）
INCLUDE = ["mnemo.db", "config.json", "skills", "plugins"]


def _derive(passphrase: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, 200_000, 32)


def _keystream(key: bytes, nonce: bytes, n: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + nonce + counter.to_bytes(8, "big")).digest()
        counter += 1
    return bytes(out[:n])


def encrypt(data: bytes, passphrase: str) -> bytes:
    salt, nonce = os.urandom(16), os.urandom(16)
    key = _derive(passphrase, salt)
    ks = _keystream(key, nonce, len(data))
    ct = bytes(a ^ b for a, b in zip(data, ks))
    mac = hmac.new(key, salt + nonce + ct, hashlib.sha256).digest()
    return MAGIC + salt + nonce + mac + ct


def decrypt(blob: bytes, passphrase: str) -> bytes:
    if blob[:len(MAGIC)] != MAGIC:
        raise ValueError("不是有效的 Mnemo 同步文件")
    body = blob[len(MAGIC):]
    salt, nonce, mac, ct = body[:16], body[16:32], body[32:64], body[64:]
    key = _derive(passphrase, salt)
    if not hmac.compare_digest(mac, hmac.new(key, salt + nonce + ct, hashlib.sha256).digest()):
        raise ValueError("口令错误或文件已损坏")
    ks = _keystream(key, nonce, len(ct))
    return bytes(a ^ b for a, b in zip(ct, ks))


def _make_tar(home: Path) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name in INCLUDE:
            p = home / name
            if p.exists():
                tar.add(p, arcname=name)
    return buf.getvalue()


def export_bundle(home: Path, out: Path, passphrase: str | None = None) -> int:
    data = _make_tar(home)
    if passphrase:
        data = encrypt(data, passphrase)
    out.write_bytes(data)
    return len(data)


def import_bundle(src: Path, home: Path, passphrase: str | None = None) -> list[str]:
    blob = src.read_bytes()
    if blob[:len(MAGIC)] == MAGIC:
        if not passphrase:
            raise ValueError("该文件已加密，请用 --passphrase 提供口令")
        blob = decrypt(blob, passphrase)
    elif passphrase:
        # 用户给了口令但文件未加密——按明文继续
        pass
    home.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        members = tar.getnames()
        try:
            tar.extractall(home, filter="data")   # 3.12+ 安全过滤
        except TypeError:
            tar.extractall(home)                   # 兼容旧版
    return members
