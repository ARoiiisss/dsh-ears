# -*- coding: utf-8 -*-
"""
demo_agent_flow.py — 端到端示例：一个 DSH agent 怎么用「耳朵」听歌并说出感受。

⚠️ 这是**示例**，把耳朵拿到的材料拼成一条提示词——但它**不替你判断**。
   真正的判断，是把「图 + 歌名 + 歌词」发给你自己的**多模态模型**，用你的人设语气说。

本示例里，"发给模型"那步用注释标出，实际请替换成你自己的模型调用
（OpenAI 兼容的 chat/completions 都行，图用 image_url 传 base64）。

用法：
    python examples/demo_agent_flow.py
"""
import os
import sys
import json
import base64
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CAP = os.path.join(ROOT, "captures")
os.makedirs(CAP, exist_ok=True)

WAV = os.path.join(CAP, "demo.wav")
PNG = os.path.join(CAP, "demo.png")


def run(script, *args):
    """跑一个耳朵脚本，解析它最后一行 JSON。"""
    py = sys.executable
    out = subprocess.run([py, os.path.join(ROOT, script), *args],
                         capture_output=True, text=True, encoding="utf-8")
    if out.returncode != 0:
        raise RuntimeError(f"{script} 失败：{out.stderr}")
    return json.loads(out.stdout.strip().splitlines()[-1])


def build_prompt(title, artist, lyric_status, lyric, seconds, shape):
    """按 SKILL.md 的模板拼提示词（这里只给最小版，正式用时把你的人设拼在最前面）。"""
    if lyric_status == "ok" and lyric:
        lyric_block = "当前这段的歌词：\n" + lyric
    elif lyric_status == "no_lyric":
        lyric_block = "这首这会儿查不到歌词（多半纯音乐/没收录）——别谈歌词，只凭声音说感受。"
    else:
        lyric_block = "这会儿没查到歌词，别编、别假装听懂词——只凭声音说感受。"

    return (
        "你正在陪我一起听歌：\n"
        f"《{title}》{('，' + artist) if artist else ''}。\n"
        f"你刚听了这首歌一段 {seconds} 秒的真实声音（下面这张图就是这段“声音的样子”："
        "横轴时间、越亮越响、下面低音上面高音）。\n"
        f"（声音走向参考：{shape}）\n"
        f"{lyric_block}\n\n"
        "就照你刚听到的这一整段，说说真实感受：喜不喜欢、心里什么感觉、想到什么。两三句，说通顺。\n"
        "🔴 中间有明显变化（憋着→炸开、变快、转安静）就点出来，别拿开头代表整首。\n"
        "🔴 别提“图/频谱”，就当亲耳听的。不要说低音/鼓/BPM 这类术语。\n"
        "🔴 歌词只有上面给了才能引用；没给就一个字都别编，别假装听懂了人声。"
    )


def main():
    print("① 录音 40s …")
    rec = run("ears_record.py", "40", WAV)

    print("② 画频谱图 …")
    ren = run("ears_render.py", WAV, PNG)

    print("③ 读当前歌名（可选，Windows）…")
    try:
        np_info = run("ears_nowplaying.py")
    except Exception:
        np_info = {}
    title = np_info.get("title", "")
    artist = np_info.get("artist", "")

    print("④ 查歌词（可选）…")
    lyric = {"status": "no_match", "text": ""}
    if title:
        try:
            lyric = run("ears_lyrics.py", title, artist)
        except Exception:
            pass

    prompt = build_prompt(title or "这段声音", artist,
                          lyric.get("status", "no_match"), lyric.get("text", ""),
                          ren["seconds"], ren["shape"])

    print("\n===== 交给你的多模态模型的提示词 =====")
    print(prompt)
    print("\n===== 要一起发过去的图 =====")
    print(PNG)

    # ---- 真正调用你的模型（示例骨架，按你的后端替换）----
    # b64 = base64.b64encode(open(PNG, "rb").read()).decode()
    # content = [{"type": "text", "text": prompt},
    #            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}}]
    # resp = your_chat(model="你的多模态模型", messages=[{"role":"user","content":content}])
    # print("她听着说：", resp)


if __name__ == "__main__":
    main()
