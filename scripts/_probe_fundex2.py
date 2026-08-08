"""Parse fundex HTML/JS for ranking AJAX."""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0"}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read()


html = Path(r"c:\Users\skytv\ENA+\data\processed\_fundex_page.html").read_text(encoding="utf-8")

# inline scripts
scripts = re.findall(r"<script[^>]*>([\s\S]*?)</script>", html, flags=re.I)
print("inline scripts", len(scripts))
for i, s in enumerate(scripts):
    if any(k in s for k in ("ajax", "$.", "fetch", "Rank", "buzz", "fx", "url", ".do")):
        print("=" * 40, "script", i, "len", len(s))
        # print interesting lines
        for line in s.splitlines():
            if any(k in line for k in ("ajax", ".do", "url", "Rank", "buzz", "list", "week", "genre")):
                print(line[:200])

common = get("https://www.fundex.co.kr/js/common.js?v=2").decode("utf-8", "replace")
utils = get("https://www.fundex.co.kr/js/utils.js?v=1").decode("utf-8", "replace")
Path(r"c:\Users\skytv\ENA+\data\processed\_fundex_common.js").write_text(common, encoding="utf-8")
Path(r"c:\Users\skytv\ENA+\data\processed\_fundex_utils.js").write_text(utils, encoding="utf-8")
print("common", len(common), "utils", len(utils))
for name, body in [("common", common), ("utils", utils)]:
    dos = sorted(set(re.findall(r'["\']([^"\']+\.do[^"\']*)["\']', body)))
    print(name, "dos", dos)
    for line in body.splitlines():
        if any(k in line for k in (".do", "ajax", "Rank", "buzz", "listUrl", "getRank")):
            if len(line.strip()) < 250:
                print(name, ">", line.strip()[:240])
