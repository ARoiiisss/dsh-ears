# -*- coding: utf-8 -*-
"""
ears_lyrics.py — （可选）按歌名查歌词，供 agent 当事实参考。

🔴 核心不是"能查到"，而是"不查错"：电脑上显示的多是作曲人（如"泽野弘之"），
   而曲库挂的是原唱歌手（如"Aimee Blackschleger"）。所以：
     · 歌名必须对得上（同/包含，且不太短）
     · 歌手只加分、不一票否决
   对不上一律返回空——**宁可没词，也绝不把别的歌的词喂给 agent**（这是被实锤过的坑）。

依赖：pip install requests
接口：网易云公开搜索（只读，无需登录）。若你的环境访问不了，可换成任意能按歌名搜的源。

用法：
    python ears_lyrics.py "No differences" "澤野弘之"
输出（JSON）：
    {"status":"ok","text":"...歌词...","src_title":"No differences","src_artist":"Aimee Blackschleger"}
    status: ok / no_match / no_lyric / error
"""
import sys, json, re

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def _norm(s):
    s = (s or "").lower()
    return re.sub(r"[\s\(\)\[\]（）【】\-_/,.·:：\'\"!?、～~]", "", s)


def _search(q, limit=15):
    import requests
    try:
        r = requests.get(
            "https://music.163.com/api/search/get/web",
            params={"s": q, "type": 1, "limit": limit},
            timeout=4,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"},
        )
        return (r.json().get("result", {}) or {}).get("songs", []) or []
    except Exception:
        return []


def _score(song, nt, na):
    sn = _norm(song.get("name", ""))
    if not nt:
        return -9
    if sn == nt:
        s = 100
    elif nt in sn or sn in nt:
        if min(len(nt), len(sn)) >= 4:
            s = 60
        else:
            return -9
    else:
        return -9
    arts = [a.get("name", "") for a in song.get("artists", [])]
    if na:
        an = "".join(_norm(a) for a in arts)
        if (na in an) or any((_norm(a) and (_norm(a) in na or na in _norm(a))) for a in arts):
            s += 40
    return s


def fetch_lyric(title, artist, pos=0.0):
    import requests
    nt, na = _norm(title), _norm(artist)
    if not nt:
        return {"status": "no_match", "text": "", "src_title": "", "src_artist": ""}
    seen, cands = set(), []
    for q in ([f"{title} {artist}".strip(), title] if artist else [title]):
        for sg in _search(q):
            if sg.get("id") in seen:
                continue
            seen.add(sg.get("id"))
            cands.append(sg)
    scored = [( _score(sg, nt, na), sg) for sg in cands]
    scored = [x for x in scored if x[0] > 0]
    if not scored:
        return {"status": "no_match", "text": "", "src_title": "", "src_artist": ""}
    scored.sort(key=lambda x: -x[0])
    pick = scored[0][1]
    src_title = pick.get("name", "")
    src_artist = "/".join(a.get("name", "") for a in pick.get("artists", []))
    try:
        r2 = requests.get(
            "https://music.163.com/api/song/lyric",
            params={"id": pick["id"], "lv": 1, "kv": 1, "tv": -1},
            timeout=4,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"},
        )
        lrc = (r2.json().get("lrc") or {}).get("lyric", "")
    except Exception:
        return {"status": "error", "text": "", "src_title": src_title, "src_artist": src_artist}

    lines = []
    for ln in lrc.splitlines():
        m = re.match(r"\[(\d+):(\d+)(?:[.:](\d+))?\](.*)", ln)
        if m and m.group(4).strip():
            t = int(m.group(1)) * 60 + int(m.group(2)) + int((m.group(3) or "0").ljust(3, "0")[:3]) / 1000.0
            lines.append((t, m.group(4).strip()))
    if not lines:
        return {"status": "no_lyric", "text": "", "src_title": src_title, "src_artist": src_artist}

    out = []
    for t, txt in lines[:40]:
        mark = "  ←正在唱" if abs(t - pos) < 8 else ""
        out.append(txt + mark)
    return {"status": "ok", "text": "\n".join(out), "src_title": src_title, "src_artist": src_artist}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print("usage: python ears_lyrics.py <title> [artist] [pos_sec]", file=sys.stderr)
        sys.exit(2)
    title = args[0]
    artist = args[1] if len(args) >= 2 else ""
    pos = float(args[2]) if len(args) >= 3 else 0.0
    print(json.dumps(fetch_lyric(title, artist, pos), ensure_ascii=False))
