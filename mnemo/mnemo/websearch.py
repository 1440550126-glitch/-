"""零依赖网页检索：DuckDuckGo HTML 端点 + 标准库解析，无需任何 API Key。

让 Agent 不仅能 web_fetch 已知 URL，还能"先搜索、再抓取"地主动发现信息。
解析与网络分离（parse_results 可离线单测）；网络失败时上层工具优雅降级。
"""
from __future__ import annotations

import html as _html
import re
import urllib.request
from urllib.parse import parse_qs, unquote, urlencode, urlparse

_RESULT = re.compile(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_SNIPPET = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>', re.S)

_UA = "Mozilla/5.0 (compatible; Mnemo/0.1; +local-ai-assistant)"
_ENDPOINT = "https://html.duckduckgo.com/html/"


def _strip(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def _real_url(href: str) -> str:
    """DuckDuckGo 结果常是 //duckduckgo.com/l/?uddg=<编码真实URL> 跳转，解出真实 URL。"""
    href = _html.unescape(href)
    if "uddg=" in href:
        if href.startswith("//"):
            full = "https:" + href
        elif href.startswith("/"):
            full = "https://duckduckgo.com" + href
        elif href.startswith("http"):
            full = href
        else:
            full = "https://duckduckgo.com/" + href
        q = parse_qs(urlparse(full).query)
        if q.get("uddg"):
            return unquote(q["uddg"][0])
    if href.startswith("//"):
        return "https:" + href
    return href


def parse_results(html_text: str, limit: int = 6) -> list[dict]:
    pairs = _RESULT.findall(html_text or "")
    snippets = _SNIPPET.findall(html_text or "")
    out: list[dict] = []
    for i, (href, title) in enumerate(pairs[:limit]):
        out.append({
            "title": _strip(_html.unescape(title)),
            "url": _real_url(href),
            "snippet": _strip(_html.unescape(snippets[i])) if i < len(snippets) else "",
        })
    return out


def search(query: str, limit: int = 6, timeout: int = 20) -> list[dict]:
    url = _ENDPOINT + "?" + urlencode({"q": query})
    req = urllib.request.Request(url, headers={"User-Agent": _UA},
                                 data=urlencode({"q": query}).encode())  # POST 更稳
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(2_000_000).decode("utf-8", "replace")
    return parse_results(raw, limit)
