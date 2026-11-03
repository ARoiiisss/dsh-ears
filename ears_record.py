# -*- coding: utf-8 -*-
"""
ears_record.py — 给 DSH agent 用的「耳朵」第 1 步：录一段电脑正在播放的声音（WASAPI loopback）。

⚠️ 这是「旁路」工具：只负责把声音录下来 / 画出来，**判断交给 agent 自己**。
   本脚本不做任何"好不好听"的判断。

用法：
    python ears_record.py            # 默认录 40 秒
    python ears_record.py 60         # 录 60 秒
    python ears_record.py 40 out/x.wav

输出（JSON，打到 stdout）：{"wav": "...", "seconds": 40.0, "loudness_db": -18.2}
"""
import sys, os, json

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
import numpy as np

SR = 48000
CH = 2


def record_loopback(seconds=40.0):
    """录一段「扬声器正在放的声音」(loopback)。返回 (mono_float32, sample_rate)。"""
    import soundcard as sc          # pip install soundcard
    spk = sc.default_speaker()
    mic = sc.get_microphone(id=str(spk.name), include_loopback=True)
    chunks = []
    with mic.recorder(samplerate=SR, channels=CH) as rec:
        need = int(seconds / 0.5)
        for _ in range(need):
            b = rec.record(numframes=int(SR * 0.5))
            chunks.append(b)
    buf = np.concatenate(chunks, axis=0)
    mono = buf.mean(axis=1) if buf.ndim > 1 else buf
    return mono.astype(np.float32), SR


def loudness_db(mono):
    rms = float(np.sqrt(np.mean(np.asarray(mono, dtype=np.float32) ** 2)) + 1e-12)
    return round(20 * np.log10(rms), 1)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    seconds = float(args[0]) if len(args) >= 1 else 40.0
    out = args[1] if len(args) >= 2 else os.path.join("captures", "ears_rec.wav")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

    mono, sr = record_loopback(seconds)
    try:
        import soundfile as sf      # pip install soundfile
        sf.write(out, mono, sr)
    except Exception:
        out = ""                    # 没装 soundfile 就只报指标，不落 wav

    print(json.dumps({
        "wav": out,
        "seconds": round(len(mono) / float(sr), 1),
        "loudness_db": loudness_db(mono),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
