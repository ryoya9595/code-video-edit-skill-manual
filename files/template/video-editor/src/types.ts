// timeline.json の形（make_edit.py build が作る）。時間はすべて「カット後のフレーム」
export type Clip = { from: number; to: number; start: number }; // from/to = 元動画のフレーム, start = 完成動画のフレーム
export type Caption = { from: number; to: number; text: string };
export type Telop = { from: number; to: number; text: string; variant: "emphasis" | "info"; position: "top" | "center" | "bottom" };
export type Insert = { from: number; to: number; file: string; layout: "right" | "full" | "pip"; caption?: string; credit?: string };
export type NamePlate = { from: number; to: number; name: string; title?: string };
export type Chapter = { from: number; title: string };

export type Timeline = {
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  source: string; // public フォルダ（=動画のフォルダ）からの相対パス
  clips: Clip[];
  captions: Caption[];
  telops: Telop[];
  inserts: Insert[];
  namePlates: NamePlate[];
  chapters: Chapter[];
  style: Partial<Style>;
};

// チャンネルの見た目。style.json で上書きする（数値は1080pの時の大きさ）
export type Style = {
  captionFont: string;
  captionWeight: string;
  captionSize: number;
  captionColor: string;
  captionStroke: string;
  captionStrokeWidth: number;
  captionBottom: number;
  telopFont: string;
  telopWeight: string;
  telopSize: number;
  telopFill: string;
  telopStroke: string;
  telopStrokeWidth: number;
  infoSize: number;
  infoColor: string;
  infoBg: string;
  accent: string;
  plateBg: string;
  plateText: string;
  insertBorder: string;
  showCaptions: boolean;
  showChapterBanner: boolean;
};

export const defaultStyle: Style = {
  captionFont: "Noto Sans JP",
  captionWeight: "900",
  captionSize: 56,
  captionColor: "#FFFFFF",
  captionStroke: "#111111",
  captionStrokeWidth: 10,
  captionBottom: 64,
  telopFont: "Dela Gothic One",
  telopWeight: "400",
  telopSize: 104,
  telopFill: "#FFE14D",
  telopStroke: "#111111",
  telopStrokeWidth: 18,
  infoSize: 58,
  infoColor: "#FFFFFF",
  infoBg: "#E8452C",
  accent: "#FFE14D",
  plateBg: "#111111",
  plateText: "#FFFFFF",
  insertBorder: "#FFFFFF",
  showCaptions: true,
  showChapterBanner: true,
};
