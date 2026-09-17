import { AbsoluteFill, Sequence } from "remotion";
import { Caption, Style } from "../types";

export const Captions: React.FC<{ items: Caption[]; style: Style; u: number }> = ({ items, style, u }) => (
  <>
    {items.map((c, i) => (
      <Sequence key={i} from={c.from} durationInFrames={c.to - c.from} layout="none">
        <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: style.captionBottom * u }}>
          <div
            style={{
              fontFamily: `"${style.captionFont}", sans-serif`,
              fontWeight: style.captionWeight as React.CSSProperties["fontWeight"],
              fontSize: style.captionSize * u,
              lineHeight: 1.25,
              color: style.captionColor,
              WebkitTextStroke: `${style.captionStrokeWidth * u}px ${style.captionStroke}`,
              paintOrder: "stroke fill",
              textAlign: "center",
              maxWidth: "88%",
              whiteSpace: "pre-wrap",
            }}
          >
            {c.text}
          </div>
        </AbsoluteFill>
      </Sequence>
    ))}
  </>
);
