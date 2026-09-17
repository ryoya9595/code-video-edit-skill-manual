"""カット計画 → Remotion用の timeline.json（＋字幕SRT・チャプター）を作る。

    python make_edit.py plan  "D:\\素材\\撮影.mp4" --work "D:\\素材\\撮影_edit"
    （edit_plan.json の manual_removals / chapters / telops / inserts / name_plates を編集）
    python make_edit.py build --work "D:\\素材\\撮影_edit"
    python make_edit.py sheet --video "<書き出した動画>" --out "<一覧画像.jpg>"   （2秒ごとのコマ一覧）

時間はすべて「元の動画の秒」で書く。build がカット後のフレームに変換する。
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

FILLERS = {"えー", "えーと", "えっと", "あー", "あのー", "あの", "うーん", "んー", "まあ", "えーっと", "そのー"}
STD_RATES = [Fraction(24000, 1001), Fraction(24), Fraction(25), Fraction(30000, 1001), Fraction(30),
             Fraction(50), Fraction(60000, 1001), Fraction(60)]


# ---------------------------------------------------------------- 素材情報
def probe(video: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(video)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit(f"ffprobe に失敗しました: {r.stderr}")
    d = json.loads(r.stdout)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    if v is None:
        sys.exit("映像トラックが見つかりません")
    rate_str = v.get("avg_frame_rate")
    raw = Fraction(rate_str if rate_str and rate_str != "0/0" else v["r_frame_rate"])
    fps = min(STD_RATES, key=lambda x: abs(float(x) - float(raw)))  # スマホ撮影の可変フレームレートも標準値に丸める
    width, height = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if abs(rot) in (90, 270):
        width, height = height, width
    return {
        "path": str(video), "duration": float(d["format"]["duration"]),
        "fps_num": fps.numerator, "fps_den": fps.denominator, "width": width, "height": height,
        "audio_channels": int(a["channels"]) if a else 0, "sample_rate": int(a["sample_rate"]) if a else 48000,
    }


def detect_silence(video: Path, noise_db: float, min_sec: float, duration: float) -> list:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vn",
                        "-af", f"silencedetect=noise={noise_db}dB:d={min_sec}", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out, start = [], None
    for line in r.stderr.splitlines():
        m = re.search(r"silence_start: (-?[\d.]+)", line)
        if m:
            start = max(0.0, float(m.group(1)))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and start is not None:
            out.append([start, float(m.group(1))])
            start = None
    if start is not None:
        out.append([start, duration])
    return out


# ---------------------------------------------------------------- 区間計算
def union(ranges):
    rs = sorted([list(r) for r in ranges if r[1] > r[0]])
    out = []
    for s, e in rs:
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def subtract(ranges, holes):
    out = []
    for s, e in ranges:
        cur = [[s, e]]
        for hs, he in holes:
            nxt = []
            for cs, ce in cur:
                if he <= cs or hs >= ce:
                    nxt.append([cs, ce])
                    continue
                if hs > cs:
                    nxt.append([cs, hs])
                if he < ce:
                    nxt.append([he, ce])
            cur = nxt
        out.extend(cur)
    return out


def load_words(work: Path):
    p = work / "transcript.json"
    if not p.exists():
        return []
    t = json.loads(p.read_text(encoding="utf-8"))
    out = []
    for seg in t["segments"]:
        for i, w in enumerate(seg["words"]):
            out.append({**w, "seg_end": i == len(seg["words"]) - 1})  # 息継ぎの切れ目（字幕の区切り候補）
    return out


# ---------------------------------------------------------------- plan
def cmd_plan(args):
    video = Path(args.video).resolve()
    work = Path(args.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    src = probe(video)
    if not (work / "transcript.json").exists() and not args.allow_no_transcript:
        sys.exit("transcript.json がありません。先に transcribe.py（手順1）を最後まで終わらせてから plan を実行してください"
                 "（文字起こしが無いと、小声の発話を守る処理とフィラー候補が効きません）")
    words = load_words(work)

    sil = detect_silence(video, args.noise, args.min_silence, src["duration"])
    auto = []
    for s, e in sil:
        ps = s if s <= 0.01 else s + args.pad          # 動画の頭の無音はパディングなしで削る
        pe = e if e >= src["duration"] - 0.01 else e - args.pad
        if pe - ps >= args.min_cut:
            auto.append([round(ps, 3), round(pe, 3)])
    # 小声で無音判定された発話は残す（文字起こしに単語がある所は削らない）
    speech = union([[w["start"] - 0.05, w["end"] + 0.05] for w in words])
    auto = [r for r in subtract(auto, speech) if r[1] - r[0] >= args.min_cut]

    fillers = []
    for w in words:
        if w["word"].strip(" 、。,.") in FILLERS:
            fillers.append({"start": w["start"], "end": w["end"], "text": w["word"].strip()})

    # BGMや環境音で「無音」にならない動画向け：話と話の間が長い所を候補として出す（自動では切らない）
    gaps = []
    for i in range(len(words) - 1):
        a, b = words[i], words[i + 1]
        g0, g1 = a["end"] + args.pad, b["start"] - args.pad
        if b["start"] - a["end"] >= args.gap and not any(x <= g0 and g1 <= y for x, y in auto):
            before = "".join(w["word"] for w in words[max(0, i - 5):i + 1]).strip()
            after = "".join(w["word"] for w in words[i + 1:i + 7]).strip()
            gaps.append({"start": round(g0, 3), "end": round(g1, 3), "length": round(b["start"] - a["end"], 2),
                         "context": f"…{before} ／ {after}…"})

    plan = {
        "source": src,
        "settings": {"noise_db": args.noise, "min_silence": args.min_silence, "pad": args.pad,
                     "min_cut": args.min_cut, "use_auto_silence": True, "use_fillers": False,
                     "caption_max_chars": 18},
        "auto_removals": [{"start": s, "end": e, "reason": "silence"} for s, e in auto],
        "filler_candidates": fillers,
        "gap_candidates": gaps,
        "manual_removals": [],
        "chapters": [],
        "telops": [],
        "inserts": [],
        "name_plates": [],
        "output_name": video.stem + "_完成",
    }
    old_path = work / "edit_plan.json"
    kept_manual = False
    if old_path.exists():  # やり直しで plan を再実行しても、Claude やユーザーが書いた編集案は残す
        old = json.loads(old_path.read_text(encoding="utf-8"))
        for k in ["manual_removals", "chapters", "telops", "inserts", "name_plates", "output_name"]:
            if old.get(k):
                plan[k] = old[k]
                kept_manual = True
        for k in ["use_fillers", "use_auto_silence", "caption_max_chars"]:
            if k in old.get("settings", {}):
                plan["settings"][k] = old["settings"][k]
    old_path.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    kept = src["duration"] - sum(e - s for s, e in union(auto))
    hints = []
    if not auto and gaps:
        hints.append("無音カットが0件です。BGMや環境音が入っている動画の可能性があります。gap_candidates（話の間が長い所）を"
                     "ユーザーに見せ、切るか確認してください（切ると、その部分のBGMもつながりが飛びます）")
    if kept_manual:
        hints.append("前回の edit_plan.json にあった編集案（manual_removals / telops など）は引き継ぎました")
    print(json.dumps({"元の尺(秒)": round(src["duration"], 1), "無音カット数": len(auto),
                      "カット後の尺(秒・無音のみ)": round(kept, 1), "フィラー候補": len(fillers),
                      "長い間の候補": len(gaps), "注意": hints,
                      "fps": f'{src["fps_num"]}/{src["fps_den"]}', "解像度": f'{src["width"]}x{src["height"]}',
                      "音声ch": src["audio_channels"], "plan": str(work / "edit_plan.json")},
                     ensure_ascii=False, indent=1))


def fmt_srt(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def fmt_chapter(t: float) -> str:
    t = int(t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ---------------------------------------------------------------- build
def cmd_build(args):
    work = Path(args.work).resolve()
    plan = json.loads((work / "edit_plan.json").read_text(encoding="utf-8"))
    src, st = plan["source"], plan["settings"]
    fps = Fraction(src["fps_num"], src["fps_den"])
    total_frames = int(round(src["duration"] * fps))

    removals = [[r["start"], r["end"]] for r in plan["manual_removals"]]
    if st.get("use_auto_silence", True):
        removals += [[r["start"], r["end"]] for r in plan["auto_removals"]]
    if st.get("use_fillers"):
        removals += [[f["start"] - 0.03, f["end"] + 0.03] for f in plan["filler_candidates"]]
    rem_frames = union([[max(0, int(round(s * fps))), min(total_frames, int(round(e * fps)))] for s, e in removals])

    keeps, cur = [], 0
    for s, e in rem_frames:
        if s > cur:
            keeps.append([cur, s])
        cur = max(cur, e)
    if cur < total_frames:
        keeps.append([cur, total_frames])
    keeps = [k for k in keeps if k[1] - k[0] >= args.min_keep_frames]  # 数フレームだけ残る破片は捨てる
    if not keeps:
        sys.exit("残る区間がありません。edit_plan.json を見直してください")

    segs, tl = [], 0  # (src_in, src_out, tl_start)（フレーム）
    for a, b in keeps:
        segs.append((a, b, tl))
        tl += b - a
    total = tl

    def to_frame(t: float, side: str):
        """元動画の秒 → カット後のフレーム。カットされた位置は start なら次の区間の頭、end なら前の区間の終わり"""
        f = t * float(fps)
        for a, b, s in segs:
            if a <= f <= b:
                return int(round(s + (f - a)))
        if side == "start":
            nxt = [s for a, b, s in segs if a > f]
            return nxt[0] if nxt else None
        prv = [s + (b - a) for a, b, s in segs if b < f]
        return prv[-1] if prv else None

    def span(item, min_frames=1):
        s, e = to_frame(float(item["start"]), "start"), to_frame(float(item["end"]), "end")
        if s is None or e is None or e - s < min_frames:
            return None
        return s, e

    def is_kept(t: float):
        f = t * float(fps)
        return any(a <= f < b for a, b, _ in segs)

    # ---- 字幕（カット後の時間軸に合わせる）
    max_chars = int(st.get("caption_max_chars", 18))
    words = [w for w in load_words(work) if is_kept((w["start"] + w["end"]) / 2)]
    cues, buf = [], []

    def buf_len():
        return len("".join(x["word"] for x in buf).strip())

    def flush():
        if not buf:
            return
        text = "".join(w["word"] for w in buf).strip().strip("、。")
        s0, e0 = to_frame(buf[0]["start"], "start"), to_frame(buf[-1]["end"], "end")
        if text and s0 is not None and e0 is not None:
            cues.append([s0, max(e0, s0 + int(round(0.6 * fps))), text])
        buf.clear()

    # 区切りの優先順: 文末 → 読点・息継ぎの切れ目（1枚に収まらない時）→ 間が空いた所
    # 長すぎる時も、単語の途中ではなく「直前の読点・息継ぎの切れ目」で分ける
    def is_soft(w):
        return w["word"].strip().endswith("、") or w.get("seg_end")

    def split_back():
        """buf を直前の区切り候補で2つに分け、前半だけ字幕にする"""
        for i in range(len(buf) - 2, 0, -1):
            if is_soft(buf[i]):
                rest = buf[i + 1:]
                del buf[i + 1:]
                flush()
                buf.extend(rest)
                return
        # 読点も息継ぎも無い長い文は、助詞のあと（「〜は」「〜で」など）で分ける
        for i in range(len(buf) - 2, 0, -1):
            head = "".join(x["word"] for x in buf[:i + 1]).strip()
            if len(head) >= 6 and buf[i]["word"].strip()[-1:] in "はがをにでともへてや":
                rest = buf[i + 1:]
                del buf[i + 1:]
                flush()
                buf.extend(rest)
                return
        flush()  # それも無ければ、仕方なくここで切る

    for wi, w in enumerate(words):
        if buf:
            gap = ((to_frame(w["start"], "start") or 0) - (to_frame(buf[-1]["end"], "end") or 0)) / float(fps)
            if gap > 0.5 or w["start"] - buf[0]["start"] > 7:
                flush()
            elif buf_len() + len(w["word"].strip()) > max_chars + 8:
                split_back()
        buf.append(w)
        tail = w["word"].strip()
        if tail.endswith(("。", "？", "！", "?", "!")):
            flush()
        elif is_soft(w) and buf_len() >= 5:
            rest = 0
            for x in words[wi + 1:]:
                rest += len(x["word"].strip())
                if x["word"].strip().endswith(("。", "？", "！", "?", "!", "、")) or x.get("seg_end"):
                    break
            if buf_len() + rest > max_chars:
                flush()
    flush()
    for i in range(len(cues) - 1):  # 次の字幕と重ならないように
        cues[i][1] = min(cues[i][1], cues[i + 1][0])
    cues = [c for c in cues if c[1] > c[0]]

    # ---- Remotion の public フォルダ（作業フォルダ\public）を用意する
    # Remotion は書き出しのたびに public フォルダを丸ごとコピーするので、動画のフォルダではなく専用フォルダにする。
    # 元動画は「ハードリンク」で置く（同じドライブなら一瞬・容量も増えない。元ファイルには何も書き込まない）
    public = work / "public"
    (public / "assets").mkdir(parents=True, exist_ok=True)
    src_path = Path(src["path"])
    linked = public / ("source" + src_path.suffix.lower())
    if not linked.exists():
        try:
            os.link(src_path, linked)
        except OSError as e:
            if not args.copy_source:
                sys.exit(f"元動画をハードリンクできませんでした（{e}）。作業フォルダを動画と同じドライブにするか、"
                         f"--copy-source を付けてコピーしてください（動画と同じ容量を使います）")
            shutil.copy2(src_path, linked)

    def rel_asset(p: str):
        """素材のパスを public からの相対パスにする。素材は 作業フォルダ\\public\\assets に置く"""
        ap = Path(p) if Path(p).is_absolute() else (public / p)
        ap = ap.resolve()
        if not ap.exists():
            sys.exit(f"素材が見つかりません: {ap}")
        try:
            return ap.relative_to(public.resolve()).as_posix()
        except ValueError:
            sys.exit(f"素材は {public / 'assets'} に置いてください: {ap}")

    telops, inserts, plates, chapters, warnings = [], [], [], [], []
    for t in plan.get("telops", []):
        sp = span(t, 3)
        if sp:
            telops.append({"from": sp[0], "to": sp[1], "text": t["text"], "variant": t.get("variant", "emphasis"),
                           "position": t.get("position", "top")})
        else:
            warnings.append(f"テロップがカットされた区間にあるので外しました: {t['text']}")
    for it in plan.get("inserts", []):
        sp = span(it, 3)
        if sp:
            inserts.append({"from": sp[0], "to": sp[1], "file": rel_asset(it["file"]),
                            "layout": it.get("layout", "right"), "caption": it.get("caption", ""),
                            "credit": it.get("credit", "")})
        else:
            warnings.append(f"素材がカットされた区間にあるので外しました: {it['file']}")
    for p in plan.get("name_plates", []):
        sp = span(p, 3)
        if sp:
            plates.append({"from": sp[0], "to": sp[1], "name": p["name"], "title": p.get("title", "")})
    chap_lines = []
    for c in sorted(plan.get("chapters", []), key=lambda c: c["start"]):
        f = to_frame(float(c["start"]), "start")
        if f is None:
            continue
        if not chapters:
            f = 0  # YouTubeのチャプターは 0:00 始まりが必須
        chapters.append({"from": f, "title": c["title"]})
        chap_lines.append(f"{fmt_chapter(f / float(fps))} {c['title']}")

    style = {}  # チャンネルの見た目。作業フォルダの style.json ＞ --style で渡したもの
    for sp in [Path(args.style) if args.style else None, work / "style.json"]:
        if sp and sp.exists():
            style.update(json.loads(sp.read_text(encoding="utf-8")))

    timeline = {
        "fps": float(fps), "width": src["width"], "height": src["height"], "durationInFrames": total,
        "source": linked.name,
        "clips": [{"from": a, "to": b, "start": s} for a, b, s in segs],
        "captions": [{"from": s, "to": e, "text": t} for s, e, t in cues],
        "telops": telops, "inserts": inserts, "namePlates": plates, "chapters": chapters,
        "style": style,
    }
    (work / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1), encoding="utf-8")

    out_dir = work / "output"
    out_dir.mkdir(exist_ok=True)
    name = plan.get("output_name") or Path(src["path"]).stem
    srt = "".join(f"{i + 1}\n{fmt_srt(s / float(fps))} --> {fmt_srt(e / float(fps))}\n{t}\n\n"
                  for i, (s, e, t) in enumerate(cues))
    (out_dir / f"{name}_字幕.srt").write_text(srt, encoding="utf-8")
    (out_dir / f"{name}_チャプター.txt").write_text("\n".join(chap_lines) + ("\n" if chap_lines else ""), encoding="utf-8")

    report = {
        "元の尺(秒)": round(src["duration"], 1), "カット後の尺(秒)": round(total / float(fps), 1),
        "カット数": len(segs) - 1, "字幕": len(cues), "テロップ": len(telops), "素材": len(inserts),
        "名前プレート": len(plates), "チャプター": len(chapters), "注意": warnings,
        "timeline": str(work / "timeline.json"), "public_dir": str(public),
        "render": f'npx remotion render Main "{out_dir / (name + ".mp4")}" --props="{work / "timeline.json"}" --public-dir="{public}"',
    }
    (work / "build_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------- sheet（検品用のコマ一覧）
def cmd_sheet(args):
    """書き出した動画から、指定秒ごとのコマを並べた一覧画像を作る（テロップのはみ出し・顔かぶりの確認用）"""
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    pattern = str(out.with_name(out.stem + "_%02d" + out.suffix))
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", args.video,
                        "-vf", f"fps=1/{args.every},scale=480:-2,tile={args.cols}x{args.rows}", pattern],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit(f"コマ一覧の作成に失敗しました: {r.stderr[-1500:]}")
    pages = sorted(out.parent.glob(out.stem + "_*" + out.suffix))
    print(json.dumps({"pages": [str(p) for p in pages], "every_sec": args.every,
                      "per_page": args.cols * args.rows}, ensure_ascii=False, indent=1))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("video")
    p.add_argument("--work", required=True)
    p.add_argument("--noise", type=float, default=-35.0, help="この音量(dB)以下を無音とみなす")
    p.add_argument("--min-silence", type=float, default=0.45, help="この秒数以上続く無音をカット対象にする")
    p.add_argument("--pad", type=float, default=0.1, help="発話の前後に残す余白(秒)。0.1なら間が0.2秒に詰まる")
    p.add_argument("--min-cut", type=float, default=0.3)
    p.add_argument("--gap", type=float, default=0.8, help="話と話の間がこの秒数以上なら「長い間の候補」に出す")
    p.add_argument("--allow-no-transcript", action="store_true", help="文字起こし無しで plan を実行する（非推奨）")
    p.set_defaults(func=cmd_plan)
    b = sub.add_parser("build")
    b.add_argument("--work", required=True)
    b.add_argument("--min-keep-frames", type=int, default=4)
    b.add_argument("--style", help="チャンネルの見た目 style.json（編集プロジェクトにあるもの）")
    b.add_argument("--copy-source", action="store_true", help="ハードリンクできない時に元動画をコピーする")
    b.set_defaults(func=cmd_build)
    s = sub.add_parser("sheet")
    s.add_argument("--video", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--every", type=float, default=2.0)
    s.add_argument("--cols", type=int, default=6)
    s.add_argument("--rows", type=int, default=6)
    s.set_defaults(func=cmd_sheet)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
