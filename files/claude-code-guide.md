# Claude Code 向け手順書：YouTube動画をコードで編集するスキルを作る

> この手順書は Claude Code が読むためのものです。ユーザーと会話しながら、上から順に進めてください。
> 配布元：https://ryoya9595.github.io/code-video-edit-skill-manual/

## 1. ゴール

ユーザーのPCに、撮影したYouTube動画を **コード（Remotion）で編集して完成mp4まで書き出す** スキル `yt-code-edit` を作り、**ユーザーの短い動画で書き出し・検品まで通す**。

完成したスキルの流れ：

```
文字起こし → 台本と突き合わせ → カット → テロップ → 素材貼り → レンダリング → 検品
```

| 工程 | 中身 |
|---|---|
| 文字起こし | faster-whisper。単語ごとの時刻つき。言い直し・フィラーも拾う |
| 台本と突き合わせ | 台本があれば、固有名詞・数字の誤変換を直す |
| カット | 0.45秒以上の間を0.2秒に詰める。言い直しは後のテイクを採用 |
| テロップ | 字幕（全編）＋強調テロップ＋名前プレート＋チャプター見出し。すべてコードで描く |
| 素材貼り | ユーザーの素材（写真・イラスト）を、右側のカード／全画面／小窓で貼る |
| レンダリング | Remotion で mp4 に書き出す |
| 検品 | 2秒ごとのコマを並べた画像を見て、はみ出し・顔かぶり・黒画面を確認 |

作らないもの：AIアバターの解説動画（声の合成・アニメーション）、BGM・効果音の自動選曲、ネットからの画像の自動取得

## 2. 守ること

- **インストール・設定の変更の前に、何をするかを説明してユーザーの了承を取る**
- 元の動画ファイルは上書き・移動・削除しない。作業ファイルは動画と同じ場所の `<動画名>_edit` フォルダに置く
- ネット上の画像を勝手に動画に使わない。素材はユーザーの手持ちか、使用許諾を確認できたものだけ
- `.env` や認証情報のファイルは読まない
- 最初の動作確認は **1〜2分の短い動画** で行う
- **文字起こしと書き出しはバックグラウンド実行にする。** Claude Code のコマンド実行は1回最大10分で打ち切られるため、長い動画では途中で止まって失敗に見える（SKILL.md の「時間がかかる処理の動かし方」参照）
- 「できた」と言う前に「8. 動作確認チェックリスト」を実際に確認する
- この手順書は Windows を前提に書いている。Mac の場合はコマンドを読み替える（`python` → `python3`、パス区切り、`%USERPROFILE%` → `~` など）

## 3. 仕組み

```
<動画名>_edit\
  transcript.json / transcript.txt   ← ① transcribe.py
  edit_plan.json                      ← ② make_edit.py plan ＋ ③ Claude が編集案を書く
  timeline.json                       ← ④ make_edit.py build（Remotion に渡すデータ）
  public\source.mp4                   ← 元動画のハードリンク（コピーしない）
  public\assets\                      ← 素材の画像
  output\<名前>.mp4 / _字幕.srt / _チャプター.txt / 検品_01.jpg …

video-editor\（Remotion の編集プロジェクト・1つだけ作る）
  style.json                          ← チャンネルの見た目（色・フォント・大きさ）
  src\Main.tsx                        ← 本編のカット＋各レイヤーを重ねる
  src\components\                     ← 字幕・テロップ・素材・名前プレート・チャプター見出しの部品
```

判断の理由（変えるときはこの理由を踏まえること）：
- **時間は edit_plan.json では「元動画の秒」で書き、build がカット後のフレームに変換する。** Claude は文字起こしの時刻をそのまま使えるので、カット後の時間を計算し間違えない
- **Remotion の public フォルダは作業フォルダの `public`。** Remotion は書き出しのたびに public フォルダを丸ごとコピーする（Windows）。動画のフォルダを指定すると他の動画までコピーしてしまう。元動画は **ハードリンク**（同じドライブなら一瞬・容量も増えない）で置く
- **見た目は style.json に集める。** ユーザーが「色を変えたい」「フォントを変えたい」と言った時に、部品のコードを触らずに直せる
- **検品は画像で見る。** 書き出した動画から2秒ごとのコマを並べた画像を作り、Claude が目で確認する

参考スクリプト・ひな形の状態：実際の撮影動画（2分・BGM入り・見出し焼き込み済み）でも、Fable 5.1 が SKILL.md だけを見て手順0〜10を最後まで進められることを確認した（編集案の確認で止まる／書き出しをバックグラウンドで待つ／検品まで）。そのテストで見つかった点は SKILL.md とスクリプトに反映済み。それ以前の確認：Mac でテスト用の日本語動画（無音と言い直し入り）を使い、文字起こし → カット計画 → timeline → 静止画チェック → 書き出し → 検品画像まで通して確認済み。字幕・強調テロップ・情報テロップ・名前プレート・チャプター見出し・素材（右カード／全画面）の表示と、style.json による色・フォント変更も確認した。**Windows での動作は、このユーザーのPCで最初に確認すること。**

## 4. フェーズA：環境の確認（読むだけ・変更なし）

PowerShellで確認し、結果をユーザーに一覧で報告する。足りないものは、入れ方を説明して了承を取ってから入れる。

```powershell
node -v; npm -v; python --version; ffmpeg -version | Select-Object -First 1; ffprobe -version | Select-Object -First 1
python -c "import faster_whisper, ctranslate2; print('faster-whisper', faster_whisper.__version__, 'cuda devices', ctranslate2.get_cuda_device_count())"
```

| 必要なもの | 目安 | ない場合 |
|---|---|---|
| Node.js | 20以上 | `winget install OpenJS.NodeJS.LTS` |
| Python | 3.10以上 | `winget install Python.Python.3.12` |
| FFmpeg / ffprobe | PATHが通っている | `winget install Gyan.FFmpeg` |
| faster-whisper | Pythonから import できる | `python -m pip install faster-whisper` |
| NVIDIA GPU | あると文字起こしが速い（なくても動く） | CPUの場合は `--model medium` などに下げる |
| ネット接続 | 初回の npm install・Chromeの自動ダウンロード・Google Fonts の読み込みに必要 | — |

- `faster_whisper` が別のPython（仮想環境など）に入っている場合は、そのPythonのパスをスキルで使う
- 動画の置き場所（ドライブ）を聞いておく。作業フォルダは動画と同じドライブに作る（ハードリンクのため）

## 5. フェーズB：編集プロジェクトとスキルを作る（要了承）

ユーザーに「編集プロジェクトを置く場所」を聞く（例：`D:\AI\video-editor`。動画と同じドライブでなくてもよい）。了承を得てから実行する。

```powershell
$base = "https://ryoya9595.github.io/code-video-edit-skill-manual/files"
$project = "D:\AI\video-editor"   # ← ユーザーに聞いた場所
$skill = "$env:USERPROFILE\.claude\skills\yt-code-edit"

# 1. 編集プロジェクト（Remotion のひな形）
$zip = "$env:TEMP\video-editor-template.zip"
Invoke-WebRequest "$base/video-editor-template.zip" -OutFile $zip
Expand-Archive $zip -DestinationPath (Split-Path $project) -Force   # video-editor フォルダができる
Set-Location $project
npm install

# 2. スキル
New-Item -ItemType Directory -Force "$skill\scripts" | Out-Null
Invoke-WebRequest "$base/transcribe.py"     -OutFile "$skill\scripts\transcribe.py"
Invoke-WebRequest "$base/make_edit.py"      -OutFile "$skill\scripts\make_edit.py"
Invoke-WebRequest "$base/SKILL_template.md" -OutFile "$skill\SKILL.md"
Get-ChildItem -Recurse $skill
```

- `Expand-Archive` は zip の中の `video-editor` フォルダを展開する。`$project` の親フォルダを指定すること。すでに同じ名前のフォルダやスキルがある場合は、上書き前にユーザーに確認する
- ダウンロードしたら中身を読み、何をするコードかをユーザーに短く説明する
- `SKILL.md` の `<SKILL_DIR>` `<PROJECT_DIR>` `<PYTHON>` を実際の値に置き換える
- Remotion のライセンス：**個人、または従業員3人以下の会社は無料（商用利用も可）**。それより大きい会社で使う場合は Company License が必要。ユーザーに一言伝える

## 6. フェーズC：チャンネルの見た目を決める

1. ユーザーに目指す見た目を聞く：自分のチャンネルのサムネ／好きなチャンネルのスクショ／色・フォントの希望
2. `video-editor\style.json` を書き換える（フォントは Google Fonts の名前）
3. ひな形のサンプルで静止画を作って見せる：

```powershell
Set-Location $project
npx remotion still Main "$env:TEMP\style-check.png" --frame=30
```

- サンプルは黒い背景に、字幕・テロップ・名前プレート・チャプター見出しが出る
- OKが出るまで直す。部品の形そのものを変えたい時は `src\components` を直す／部品を足す（足したら `src\types.ts` と `make_edit.py` の build にも項目を足す）
- 初回の `npx remotion still` / `render` では、描画用の Chrome が自動でダウンロードされる（少し時間がかかる）

## 7. フェーズD：短い動画で通しの動作確認

ユーザーに1〜2分の短い動画を選んでもらい、SKILL.md の手順0〜10をそのまま通す。
- 素材の確認用に、ユーザーの手持ちの画像を1枚 `public\assets` に置いてもらい、1か所に貼る
- 初回の文字起こしでは、文字起こしモデル（large-v3・約3GB）のダウンロードで10〜20分かかる。始める前にユーザーに伝える（faster-whisper の動作確認でモデルが既に入っていれば不要）
- レンダリングにかかった時間を測り、「動画1分あたり何分かかるか」をユーザーに伝える（長い動画の目安になる）。スキルのフォルダに `render_speed.md` を作って1行目の記録を書く（以後は SKILL.md の手順8が書き足していく）
- 短い動画でも、文字起こしと書き出しは **本番と同じくバックグラウンド実行＋ログファイル** で動かし、通知が来てからログを確認する流れを一度通しておく

## 8. 動作確認チェックリスト

以下を **全部確認してから** 完成と報告する。

| # | 確認すること | 見る場所 |
|---|---|---|
| 1 | 文字起こしがGPUで動いた（ログに `device=cuda`） | transcribe の出力 |
| 2 | 言い直しの前のテイクが消えて、話が自然につながっている | 完成mp4（ユーザーに聞く） |
| 3 | 元の動画ファイルが変わっていない。`public\source.*` はハードリンク | 更新日時・`fsutil hardlink list` |
| 4 | 字幕がセリフと合っている（動画の後半でもズレない） | 完成mp4 |
| 5 | テロップ・名前プレート・素材が狙った時間に出て、顔にかぶっていない | 検品画像・完成mp4 |
| 6 | つなぎ目で音が「プツッ」と鳴らない。映像と音がズレていない | 完成mp4（ユーザーに聞く） |
| 7 | フォントが指定どおり（四角や別のフォントになっていない） | 検品画像 |
| 8 | チャプターのテキストが 0:00 から始まっている | output の _チャプター.txt |

## 9. つまずいた時

| 症状 | 見るところ・直し方 |
|---|---|
| `build` で「ハードリンクできませんでした」 | 作業フォルダが動画と別のドライブ。動画と同じドライブにするか、`--copy-source` を付ける（動画と同じ容量を使うのでユーザーに確認） |
| 書き出しや文字起こしが途中で止まった・失敗扱いになった | 10分の実行上限で打ち切られている。バックグラウンド実行（run_in_background）＋ログファイルでやり直す。output に途中までの mp4 が残っていたら消してから再実行 |
| 書き出しの開始までが長い | public フォルダ（元動画）のコピーに時間がかかっている。動画が大きいほど長い。故障ではない |
| `delayRender` がタイムアウト | フォントか動画の読み込み待ち。ネット接続と style.json のフォント名を確認。`--timeout=120000` を付ける |
| フォントが四角・別のフォント | Google Fonts に無い名前。正しい名前（例：`Dela Gothic One`）に直す |
| レンダリングが遅い | `--concurrency` を上げ下げして速い値を探す。他のアプリを閉じる。まず短い範囲だけ `--frames=0-899` で試す |
| 映像と音が少しずつズレる | スマホ撮影の可変フレームレート。元動画を固定フレームレートに変換したコピーを作り、そちらを編集する（元ファイルは残す） |
| 言葉の頭や語尾が切れる | plan の `--pad` を 0.15〜0.2 に、`--noise` を -40 に |
| 間が残りすぎ | `--min-silence` を 0.35、`--pad` を 0.08 に |
| 無音カットが0件になる | BGMや環境音が入っている動画。plan の出力の gap_candidates（話の間が長い所）をユーザーに見せて、切るか決めてもらう。`--noise` を上げても BGM ごと切れるだけなので勧めない |
| 字幕が単語の途中で切れる | transcript.json の words に句読点がほとんど無い時に起きやすい。make_edit.py は「息継ぎの切れ目（セグメントの終わり）」でも区切るので、最新の make_edit.py か確認する。それでも気になる所は words[].word の末尾に「、」を足す |
| 強調テロップが変な所で改行される | 1行が全角12文字を超えている。edit_plan.json の text に `\n` で改行位置を入れる |
| テロップが顔にかぶる | edit_plan.json の telops の `position`、inserts の `layout` を変える。よく起きるなら style.json や部品の位置を直す |

直したら **スクリプト・SKILL.md・style.json の必要な所に反映** し、同じ短い動画でもう一度チェックリストを通す。

## 10. 完成後にユーザーへ伝えること

- 使い方：「この動画を編集して：D:\...\撮影.mp4（台本：D:\...\台本.txt／素材：D:\...\素材フォルダ）」
- 途中で「消す言い直し・テロップ・素材・チャプターの案」を確認されるので、直したい所を伝える
- 見た目を変えたい時：「テロップを○○っぽくして」「フォントを△△に」
- 好みの直し方は、最後に「スキルに反映して」と言えば次回からも同じになる
- 作業フォルダの `public\source.*` は元動画のハードリンク。消しても元動画は消えない

---
参考：Remotion https://www.remotion.dev/ （ライセンス：https://www.remotion.dev/docs/license）
