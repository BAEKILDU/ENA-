"""Call fundex ranking API and dump response."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

UA = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.fundex.co.kr/fxmain.do",
}


def post(url: str, data: dict) -> str:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={**UA, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


html = Path(r"c:\Users\skytv\ENA+\data\processed\_fundex_page.html").read_text(encoding="utf-8")
# extract getOqlistNew ajax block
m = re.search(r"function getOqlist[\s\S]{0,200}getOqlistNew[\s\S]{0,2500}error\s*:", html)
if not m:
    # broader
    idx = html.find("getOqlistNew")
    print("idx", idx)
    print(html[idx - 800 : idx + 1200])
else:
    print(m.group(0)[:2000])

# try posts
base = "https://www.fundex.co.kr/"
variants = [
    {
        "wtype": "week",
        "table": "tvr_week_rank_nor",
        "is_ott": "tv",
        "genre": "ALL",
        "oq": "buzz",
    },
    {
        "wtype": "week",
        "table": "tvr_week_rank_nor",
        "is_ott": "tv",
        "cat": "ALL",
    },
    {"wtype": "week", "table": "tvr_week_rank_nor", "is_ott": "tv"},
    {"wtype": "week", "table": "v_tvr_week_rank_ott", "is_ott": "ott"},
    {"wtype": "week", "table": "tvr_week_rank_nor_ott", "is_ott": "ott"},
]

for i, params in enumerate(variants):
    for path in ("select/nowplay.getOqlistNew.do", "select/nowplay.topPjlistOq.do"):
        try:
            text = post(base + path, params)
            print("=" * 40, path, params)
            print(text[:500])
            Path(rf"c:\Users\skytv\ENA+\data\processed\_fundex_api_{i}_{path.split('.')[-2]}.json").write_text(
                text, encoding="utf-8"
            )
        except Exception as exc:
            print("FAIL", path, params, exc)
