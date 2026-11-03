# -*- coding: utf-8 -*-
"""
ears_nowplaying.py — （可选，仅 Windows）读电脑当前正在播放的歌名/歌手/进度。

原理：Windows SMTC（系统媒体传输控件）。QQ音乐/网易云/Spotify/浏览器等只要接入了系统媒体控制，
      不用管它是哪个 App，都能读到。

依赖：pip install winsdk

用法：
    python ears_nowplaying.py

输出（JSON）：{"title": "No differences", "artist": "澤野弘之", "album": "...", "pos": 56.2}
读不到就输出 {}。
"""
import sys, json, asyncio

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def now_playing():
    try:
        from winsdk.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as SM,
        )

        async def _g():
            mgr = await SM.request_async()
            for s in mgr.get_sessions():
                info = await s.try_get_media_properties_async()
                tl = s.get_timeline_properties()
                return {
                    "title": info.title or "",
                    "artist": info.artist or "",
                    "album": info.album_title or "",
                    "pos": float(tl.position.total_seconds()) if tl else 0.0,
                }
            return {}

        return asyncio.run(_g())
    except Exception:
        return {}


if __name__ == "__main__":
    print(json.dumps(now_playing() or {}, ensure_ascii=False))
