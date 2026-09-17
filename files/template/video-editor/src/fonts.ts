import { useEffect, useState } from "react";
import { cancelRender, continueRender, delayRender } from "remotion";
import { getAvailableFonts } from "@remotion/google-fonts";

// style.json に書いた Google Fonts 名を、描画前に読み込む
export const useGoogleFonts = (families: { family: string; weight: string }[]) => {
  const [handle] = useState(() => delayRender("Google Fonts を読み込み中"));
  const key = JSON.stringify(families);
  useEffect(() => {
    const all = getAvailableFonts();
    Promise.all(
      families.map(async ({ family, weight }) => {
        const entry = all.find((f) => f.fontFamily === family);
        if (!entry) {
          console.warn(`Google Fonts に見つからないフォント: ${family}（PCに入っているフォントとして扱います）`);
          return;
        }
        const mod = await entry.load();
        const { waitUntilDone } = mod.loadFont("normal", { weights: [weight], ignoreTooManyRequestsWarning: true });
        await waitUntilDone();
      })
    )
      .then(() => continueRender(handle))
      .catch((err) => cancelRender(err));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
};
