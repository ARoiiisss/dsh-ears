# -*- coding: utf-8 -*-
"""
ears_render.py — 给 DSH agent 用的「耳朵」第 2 步：把一段 wav 画成「声音的样子」（频谱图 PNG）。

🔴 为什么画图而不是报一堆数字：agent 是「看图 + 读字」的模型，一张频谱图能直接看出
   起伏、明暗、节奏、有没有高潮——比给一串 BPM/低音比例强得多，也更不容易被误读。
   （实测踩过：同一首歌不同片段，BPM 报出 99/136/78 三个值，纯噪声。）

用法：
    python ears_render.py captures/ears_rec.wav
    python ears_render.py captures/ears_rec.wav out/spectrogram.png

输出（JSON，打到 stdout）：
    {"png": "...", "seconds": 40.0, "shape": "越到后面越有劲、越满；音色从偏闷慢慢打开、变亮；中间有起落"}
    shape 是**诚实的走向描述**（前/中/后三段的响度、明暗、起伏），供 agent 当事实参考。
"""
import sys, os, json

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
import numpy as np


def _load(path, target_sr=22050):
    import librosa                 # pip install librosa
    y, sr = librosa.load(path, sr=None, mono=True)
    if sr != target_sr:
        y = librosa.resample(y.astype(np.float32), orig_sr=sr, target_sr=target_sr)
    return y.astype(np.float32), target_sr


def describe_shape(y, sr):
    """前/中/后三段 → 响度走向 + 明暗走向 + 起伏。只说趋势，不评价好坏。"""
    import librosa
    if len(y) < sr * 4:
        return ""
    thirds = np.array_split(y, 3)

    def stats(seg):
        r = float(np.sqrt(np.mean(seg ** 2)))
        c = float(np.mean(librosa.feature.spectral_centroid(y=seg, sr=sr)[0]))
        return r, c

    (r0, c0), (r1, c1), (r2, c2) = [stats(s) for s in thirds]
    if r2 > r0 * 1.5:
        eng = "越到后面越有劲、越满"
    elif r2 < r0 * 0.66:
        eng = "越到后面越收、越轻"
    else:
        eng = "响度前后差不多"
    if c2 > c0 * 1.25:
        tone = "音色从偏闷慢慢打开、变亮"
    elif c2 < c0 * 0.8:
        tone = "音色从亮慢慢沉下去、变暗"
    else:
        tone = "明暗前后差不多"
    rv = float(np.std([r0, r1, r2]) / (np.mean([r0, r1, r2]) + 1e-9))
    und = "中间有起落" if rv > 0.15 else "整体比较平"
    return f"{eng}；{tone}；{und}"


def render(wav, png, title=""):
    import librosa
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    # 中文字体（有就用，没有会退化成方框，不影响机器看）
    for fp in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
               "/System/Library/Fonts/PingFang.ttc", "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"]:
        if os.path.exists(fp):
            try:
                fm.fontManager.addfont(fp)
                plt.rcParams["font.sans-serif"] = [fm.FontProperties(fname=fp).get_name()]
                break
            except Exception:
                pass
    plt.rcParams["axes.unicode_minus"] = False

    y, sr = _load(wav)
    r = librosa.feature.rms(y=y, hop_length=512)[0]
    rdb = 20 * np.log10(np.maximum(r, 1e-8))
    dur = len(y) / float(sr)
    w = max(12.0, min(30.0, dur * 0.55))
    plt.figure(figsize=(w, 5.2))
    D = librosa.amplitude_to_db(np.abs(librosa.stft(y, n_fft=2048, hop_length=512)), ref=np.max)
    librosa.display.specshow(D, sr=sr, hop_length=512, x_axis="time", y_axis="log", cmap="magma")
    plt.colorbar(format="%+2.0f dB")
    ax = plt.gca()
    ax2 = ax.twinx()
    tt = librosa.frames_to_time(np.arange(len(r)), sr=sr, hop_length=512)
    ax2.plot(tt, rdb, color="cyan", lw=0.8, alpha=0.75)
    ax2.set_ylim(rdb.min(), 0)
    ax2.set_ylabel("RMS dB", color="cyan")
    plt.title("频谱图 + 响度  |  " + (title or os.path.basename(wav)))
    plt.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(png)), exist_ok=True)
    plt.savefig(png, dpi=90)
    plt.close()

    return {
        "png": png,
        "seconds": round(dur, 1),
        "shape": describe_shape(y, sr),
    }


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print("usage: python ears_render.py <wav> [out.png]", file=sys.stderr)
        sys.exit(2)
    wav = args[0]
    png = args[1] if len(args) >= 2 else os.path.join("captures", "spectrogram.png")
    print(json.dumps(render(wav, png), ensure_ascii=False))


if __name__ == "__main__":
    main()
