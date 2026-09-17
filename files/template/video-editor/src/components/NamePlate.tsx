import { AbsoluteFill, Easing, interpolate, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { NamePlate, Style } from "../types";

const One: React.FC<{ p: NamePlate; style: Style; u: number }> = ({ p, style, u }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const len = p.to - p.from;
  const slide = Math.min(
    interpolate(frame, [0, 0.3 * fps], [0, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }),
    interpolate(frame, [len - 0.25 * fps, len], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
  );
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: 60 * u,
          bottom: 190 * u,
          transform: `translateX(${(slide - 1) * 500 * u}px)`,
          opacity: slide,
          fontFamily: `"${style.captionFont}", sans-serif`,
        }}
      >
        {p.title ? (
          <div style={{ display: "inline-block", background: style.accent, color: "#111", fontWeight: 900, fontSize: 28 * u, padding: `${4 * u}px ${16 * u}px` }}>
            {p.title}
          </div>
        ) : null}
        <div
          style={{
            background: style.plateBg,
            color: style.plateText,
            fontWeight: 900,
            fontSize: 52 * u,
            padding: `${10 * u}px ${28 * u}px`,
            borderLeft: `${12 * u}px solid ${style.accent}`,
          }}
        >
          {p.name}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const NamePlateLayer: React.FC<{ items: NamePlate[]; style: Style; u: number }> = ({ items, style, u }) => (
  <>
    {items.map((p, i) => (
      <Sequence key={i} from={p.from} durationInFrames={p.to - p.from} layout="none">
        <One p={p} style={style} u={u} />
      </Sequence>
    ))}
  </>
);
