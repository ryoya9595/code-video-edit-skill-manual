import { AbsoluteFill, Easing, interpolate, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { Chapter, Style } from "../types";

const SHOW_SEC = 3.5;

const One: React.FC<{ c: Chapter; n: number; style: Style; u: number }> = ({ c, n, style, u }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const len = Math.round(SHOW_SEC * fps);
  const v = Math.min(
    interpolate(frame, [0, 0.35 * fps], [0, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }),
    interpolate(frame, [len - 0.3 * fps, len], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
  );
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          top: 40 * u,
          left: 0,
          transform: `translateX(${(v - 1) * 700 * u}px)`,
          display: "flex",
          alignItems: "stretch",
          fontFamily: `"${style.captionFont}", sans-serif`,
          fontWeight: 900,
          boxShadow: `0 ${8 * u}px ${20 * u}px rgba(0,0,0,.35)`,
        }}
      >
        <div style={{ background: "#111", color: style.accent, fontSize: 30 * u, padding: `${12 * u}px ${20 * u}px`, display: "flex", alignItems: "center" }}>
          {String(n).padStart(2, "0")}
        </div>
        <div style={{ background: style.accent, color: "#111", fontSize: 40 * u, padding: `${10 * u}px ${34 * u}px` }}>{c.title}</div>
      </div>
    </AbsoluteFill>
  );
};

export const ChapterBanner: React.FC<{ items: Chapter[]; style: Style; u: number }> = ({ items, style, u }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {items.map((c, i) => (
        <Sequence key={i} from={c.from} durationInFrames={Math.round(SHOW_SEC * fps)} layout="none">
          <One c={c} n={i + 1} style={style} u={u} />
        </Sequence>
      ))}
    </>
  );
};
