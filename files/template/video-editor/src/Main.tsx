import { AbsoluteFill, OffthreadVideo, Sequence, staticFile, useVideoConfig } from "remotion";
import { useGoogleFonts } from "./fonts";
import { defaultStyle, Style, Timeline } from "./types";
import { Captions } from "./components/Captions";
import { TelopLayer } from "./components/Telop";
import { InsertLayer } from "./components/Insert";
import { NamePlateLayer } from "./components/NamePlate";
import { ChapterBanner } from "./components/ChapterBanner";

export const Main: React.FC<Timeline> = (props) => {
  const style: Style = { ...defaultStyle, ...props.style };
  const { height } = useVideoConfig();
  const u = height / 1080; // 1080p基準の大きさを、実際の解像度に合わせる倍率

  useGoogleFonts([
    { family: style.captionFont, weight: style.captionWeight },
    { family: style.telopFont, weight: style.telopWeight },
  ]);

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* 1. カット済みの本編（残す区間を順番に並べる） */}
      {props.clips.map((c, i) => {
        const len = c.to - c.from;
        return (
          <Sequence key={i} from={c.start} durationInFrames={len} layout="none">
            <OffthreadVideo
              src={staticFile(props.source)}
              trimBefore={c.from}
              trimAfter={c.to}
              // つなぎ目で「プツッ」と鳴らないように、前後2フレームだけ音量をなめらかに
              volume={(f) => Math.max(0, Math.min(1, (f + 1) / 3, (len - f) / 3))}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </Sequence>
        );
      })}

      {/* 2. 素材（写真・イラスト） */}
      <InsertLayer items={props.inserts} style={style} u={u} />

      {/* 3. 名前プレート */}
      <NamePlateLayer items={props.namePlates} style={style} u={u} />

      {/* 4. チャプターの見出し */}
      {style.showChapterBanner && <ChapterBanner items={props.chapters} style={style} u={u} />}

      {/* 5. 字幕（全編） */}
      {style.showCaptions && <Captions items={props.captions} style={style} u={u} />}

      {/* 6. 強調テロップ（いちばん上） */}
      <TelopLayer items={props.telops} style={style} u={u} />
    </AbsoluteFill>
  );
};
