import { AbsoluteFill, Easing, interpolate, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { Style, Telop } from "../types";

const One: React.FC<{ t: Telop; style: Style; u: number }> = ({ t, style, u }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const len = t.to - t.from;
  // ポンッと出て、最後にすっと消える
  const pop = interpolate(frame, [0, 0.18 * fps], [0.6, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.back(2)) });
  const fade = interpolate(frame, [len - 0.15 * fps, len], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const justify = t.position === "center" ? "center" : t.position === "bottom" ? "flex-end" : "flex-start";
  const pad = t.position === "bottom" ? { paddingBottom: 190 * u } : { paddingTop: 150 * u }; // 上はチャプター見出しと重ならない高さ

  if (t.variant === "info") {
    return (
      <AbsoluteFill style={{ justifyContent: justify, alignItems: "center", ...pad, opacity: fade }}>
        <div
          style={{
            transform: `scale(${pop})`,
            background: style.infoBg,
            color: style.infoColor,
            fontFamily: `"${style.captionFont}", sans-serif`,
            fontWeight: 900,
            fontSize: style.infoSize * u,
            padding: `${14 * u}px ${36 * u}px`,
            borderRadius: 12 * u,
            boxShadow: `0 ${8 * u}px 0 rgba(0,0,0,.35)`,
            maxWidth: "86%",
            textAlign: "center",
          }}
        >
          {t.text}
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ justifyContent: justify, alignItems: "center", ...pad, opacity: fade }}>
      <div
        style={{
          transform: `scale(${pop}) rotate(-2deg)`,
          fontFamily: `"${style.telopFont}", sans-serif`,
          fontWeight: style.telopWeight as React.CSSProperties["fontWeight"],
          fontSize: style.telopSize * u,
          lineHeight: 1.15,
          color: style.telopFill,
          WebkitTextStroke: `${style.telopStrokeWidth * u}px ${style.telopStroke}`,
          paintOrder: "stroke fill",
          textShadow: `0 ${10 * u}px 0 rgba(0,0,0,.45)`,
          textAlign: "center",
          maxWidth: "90%",
          whiteSpace: "pre-wrap",
        }}
      >
        {t.text}
      </div>
    </AbsoluteFill>
  );
};

export const TelopLayer: React.FC<{ items: Telop[]; style: Style; u: number }> = ({ items, style, u }) => (
  <>
    {items.map((t, i) => (
      <Sequence key={i} from={t.from} durationInFrames={t.to - t.from} layout="none">
        <One t={t} style={style} u={u} />
      </Sequence>
    ))}
  </>
);
