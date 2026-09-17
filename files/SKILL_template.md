---
name: yt-code-edit
description: 撮影したYouTube動画(mp4等)を、文字起こし→台本と突き合わせ→カット→テロップ→素材貼り→レンダリング→検品まで、コード(Remotion)で編集して完成mp4・字幕SRT・YouTubeチャプターを作る。「この動画を編集して」「動画編集して」「テロップ入れて」「ジェットカット」「チャンネルの見た目を作って」「テロップのデザイン変えて」で発動。
---

# YouTube動画をコードで編集する（Remotion）

## 編集ルール（最優先・上から順に大事）
1. 発言の意味を変えない。迷ったら残す
2. 言い直しは「後のテイク」を採用し、前のテイクを消す
3. 固有名詞・数字は台本（あれば）に合わせて表記を統一する
4. テロップは「強調したい一言」だけ。同時に出すのは1つまで。字幕と同じ文をテロップにしない
5. 顔や大事な画面の上にテロップ・素材を重ねない（検品で必ず確認）
6. 派手さは最後。まず見やすさ

## 場所
- スキル：<SKILL_DIR>
- 編集プロジェクト（Remotion）：<PROJECT_DIR>
- Python：<PYTHON>
- 作業フォルダ：動画と同じ場所の「<動画名>_edit」（元の動画は触らない）
- チャンネルの見た目：<PROJECT_DIR>\style.json（作業フォルダに style.json があればそちらを優先）

## 手順
1. **文字起こし**
   <PYTHON> "<SKILL_DIR>\scripts\transcribe.py" "<動画>" --work "<作業フォルダ>" --prompt "<固有名詞をカンマ区切り>"
2. **カット計画**（無音の検出）
   <PYTHON> "<SKILL_DIR>\scripts\make_edit.py" plan "<動画>" --work "<作業フォルダ>"
3. **台本と突き合わせ**：台本があれば読み、transcript.json の words[].word の固有名詞・数字の誤変換を直す（字幕に反映される）
4. **編集案を作る**：transcript.txt を全部読み、edit_plan.json に書く（時間はすべて元動画の秒）
   - manual_removals：言い直しの前のテイク・言い間違い・「今のカットで」等。{"start","end","reason":"理由とセリフ"}
     - 言い直しは「前のテイクの開始 〜 後のテイクの開始の直前」を消す。単語の時刻は transcript.json の words を見る
   - chapters：話題の切れ目。{"start","title"}（最初は動画の頭）
   - telops：強調したい一言。{"start","end","text","variant":"emphasis|info","position":"top|center|bottom"}
     - emphasis＝大きい強調文字（1本の動画で多くても1分に1〜2個）／info＝数字や要点の帯
   - name_plates：自己紹介・ゲスト登場の所。{"start","end","name","title"}
   - inserts：話に出てくる物の写真・図。{"start","end","file":"assets/ファイル名","layout":"right|full|pip","caption","credit"}
     - 素材は「作業フォルダ\public\assets」に置く。使うのは**ユーザーの素材フォルダの画像**か、**使用許諾を確認できた画像**だけ。ネットの画像を勝手に使わない。出典が必要なものは credit に書く
     - 素材が足りない所は、ユーザーに「ここに○○の画像があると良い」と一覧で伝える
5. **ユーザーに確認**：カット後の尺の見込み、消す言い直しの一覧（時刻＋セリフ）、テロップ・素材・チャプターの案。OKが出るまで先に進まない
6. **timeline を作る**
   <PYTHON> "<SKILL_DIR>\scripts\make_edit.py" build --work "<作業フォルダ>" --style "<PROJECT_DIR>\style.json"
   - build_report.json の「注意」を必ず読む
7. **静止画で見た目チェック**（書き出し前に数か所だけ）
   cd "<PROJECT_DIR>"
   npx remotion still Main "<作業フォルダ>\output\check_<フレーム>.png" --frame=<フレーム> --props="<作業フォルダ>\timeline.json" --public-dir="<作業フォルダ>\public"
   - テロップ・名前プレート・素材が出るフレームを選んで画像を見る。顔にかぶる・はみ出す時は position / layout を変えて 6 からやり直す
8. **レンダリング**（時間がかかるので、始める前に目安を伝える）
   cd "<PROJECT_DIR>"
   npx remotion render Main "<作業フォルダ>\output\<名前>.mp4" --props="<作業フォルダ>\timeline.json" --public-dir="<作業フォルダ>\public" --concurrency=50%
9. **検品**
   <PYTHON> "<SKILL_DIR>\scripts\make_edit.py" sheet --video "<作業フォルダ>\output\<名前>.mp4" --out "<作業フォルダ>\output\検品.jpg"
   - 出てきた検品_01.jpg〜を全部見る（2秒ごと・1枚36コマ）。テロップのはみ出し、顔かぶり、黒い画面、字幕の出っぱなしがないか
   - 問題があれば edit_plan.json を直して 6 からやり直す
10. **完了報告**：完成mp4、カット後の尺、テロップ・素材の数、YouTube概要欄に貼るチャプター（output\<名前>_チャプター.txt の中身）、字幕SRT

## チャンネルの見た目を作る・変える
- ユーザーに「目指す見た目」を聞く（自分のチャンネルのサムネ・好きなチャンネルのスクショ・色やフォントの希望）
- <PROJECT_DIR>\style.json を書き換える。フォントは Google Fonts の名前で指定（例：Dela Gothic One / Noto Sans JP / M PLUS Rounded 1c / RocknRoll One / Zen Maru Gothic）
- 見た目をもっと大きく変える時は <PROJECT_DIR>\src\components の部品を直す／新しい部品を足す（例：実績の帯、額縁、ランキング表）。足したら types.ts と make_edit.py の build にも項目を足す
- 変えたら手順7の静止画で確認して、ユーザーのOKをもらう

## 調整できる値
- plan：--noise（無音とみなす音量dB。既定 -35、環境音が大きい部屋なら -30）／--min-silence（既定 0.45）／--pad（既定 0.1）
- edit_plan.json の settings：caption_max_chars（字幕1枚の目安文字数。既定 18）／use_fillers（true で「えー」等も切る）
- style.json：showCaptions（false で字幕を焼き込まない。YouTubeにSRTを上げる運用の時）
- ユーザーから好みの指示が出て「スキルに反映して」と言われたら、このSKILL.mdの編集ルール・既定値・style.json を更新する
