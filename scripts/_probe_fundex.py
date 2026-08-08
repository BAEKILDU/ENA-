"""Probe fundex page for data endpoints."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", "replace")


def post(url: str, data: dict) -> str:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers={**UA, "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", "replace")


html = get("https://www.fundex.co.kr/fxmain.do")
Path(r"c:\Users\skytv\ENA+\data\processed\_fundex_page.html").write_text(html, encoding="utf-8")
print("html_len", len(html))

# script/src and .do links
for m in sorted(set(re.findall(r'(?:href|src|action)=["\']([^"\']+)["\']', html))):
    if any(k in m.lower() for k in ("fx", "ajax", "api", "json", "rank", "list", "data", ".do", ".js")):
        print("LINK", m)

# try common endpoints
candidates = [
    "https://www.fundex.co.kr/fxRankList.do",
    "https://www.fundex.co.kr/fxmainRank.do",
    "https://www.fundex.co.kr/getFxRank.do",
    "https://www.fundex.co.kr/fx/getRankList.do",
    "https://www.fundex.co.kr/ajax/fxRankList.do",
    "https://www.fundex.co.kr/fxTvOttRank.do",
]
for url in candidates:
    try:
        text = get(url)
        print("OK", url, len(text), text[:120].replace("\n", " "))
    except Exception as exc:
        print("FAIL", url, type(exc).__name__, str(exc)[:80])

# search js files referenced
js_files = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', html)
print("JS", js_files)
for js in js_files[:8]:
    url = js if js.startswith("http") else urllib.parse.urljoin("https://www.fundex.co.kr/", js)
    try:
        body = get(url)
        hits = sorted(set(re.findall(r'["\'](/[^"\']*(?:Rank|rank|fx|Fx|buzz|Buzz|list)[^"\']*)["\']', body)))
        print("JSFILE", url, "hits", hits[:20])
        # also .do urls
        dos = sorted(set(re.findall(r'["\']([^"\']+\.do[^"\']*)["\']', body)))
        print("  dos", dos[:30])
    except Exception as exc:
        print("JSFAIL", url, exc)
