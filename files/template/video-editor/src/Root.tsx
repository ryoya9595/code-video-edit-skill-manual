import { Composition } from "remotion";
import { Main } from "./Main";
import { Timeline } from "./types";
import sample from "./sample-timeline.json";
import style from "../style.json"; // サンプル表示にも style.json の見た目を使う

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Main"
      component={Main}
      defaultProps={{ ...(sample as unknown as Timeline), style }}
      // 長さ・fps・サイズは timeline.json から決める
      calculateMetadata={({ props }) => ({
        durationInFrames: Math.max(1, props.durationInFrames),
        fps: props.fps,
        width: props.width,
        height: props.height,
      })}
    />
  );
};
