import { AbsoluteFill, Easing, Img, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Insert, Style } from "../types";

const One: React.FC<{ it: Insert; style: Style; u: number }> = ({ it, style, u }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const len = it.to - it.from;
  const inOut = Math.min(
    interpolate(frame, [0, 0.25 * fps], [0, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }),
    interpolate(frame, [len - 0.2 * fps, len], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
  );
  const credit = it.credit ? (
    <div style={{ position: "absolute", right: 12 * u, bottom: 8 * u, fontSize: 18 * u, color: "#fff", textShadow: "0 0 4px #000" }}>
      {it.credit}
    </div>
  ) : null;

  if (it.layout === "full") {
    const zoom = interpolate(frame, [0, len], [1, 1.08]); // ゆっくり寄る
    return (
      <AbsoluteFill style={{ opacity: inOut, backgroundColor: "#000" }}>
        <Img src={staticFile(it.file)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})` }} />
        {credit}
      </AbsoluteFill>
    );
  }
  const isPip = it.layout === "pip";
  const box: React.CSSProperties = isPip
    ? { top: 50 * u, right: 50 * u, width: "30%" }
    : { top: "12%", right: "4%", width: "46%" };
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          ...box,
          opacity: inOut,
          transform: `translateX(${(1 - inOut) * 60 * u}px) rotate(${isPip ? 0 : 1.5}deg)`,
          background: style.insertBorder,
          padding: 10 * u,
          borderRadius: 18 * u,
          boxShadow: `0 ${14 * u}px ${30 * u}px rgba(0,0,0,.45)`,
        }}
      >
        <div style={{ position: "relative" }}>
          <Img src={staticFile(it.file)} style={{ width: "100%", display: "block", borderRadius: 10 * u }} />
          {credit}
        </div>
        {it.caption ? (
          <div
            style={{
              fontFamily: `"${style.captionFont}", sans-serif`,
              fontWeight: 900,
              fontSize: 34 * u,
              color: "#111",
              textAlign: "center",
              paddingTop: 8 * u,
            }}
          >
            {it.caption}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

export const InsertLayer: React.FC<{ items: Insert[]; style: Style; u: number }> = ({ items, style, u }) => (
  <>
    {items.map((it, i) => (
      <Sequence key={i} from={it.from} durationInFrames={it.to - it.from} layout="none">
        <One it={it} style={style} u={u} />
      </Sequence>
    ))}
  </>
);
