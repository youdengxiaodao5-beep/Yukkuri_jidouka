# crispy-spork — ゆっくり解説自動生成ツール（最小サンプル）

概要
- トピック文字列から音声を生成し、背景＋立ち絵＋字幕付き MP4 を作る最小実装のサンプルです。
- ライセンス: MIT（LICENSE ファイル参照）

動作環境（Windows）
- Python 3.10+
- ffmpeg（PATHに追加）
- VOICEVOX（Editor を起動してローカル API を使用）
- 仮想環境推奨（venv）

クイックスタート
1. リポジトリをクローンまたはファイルを取得
2. 仮想環境作成・有効化:
   python -m venv venv
   .\venv\Scripts\Activate.ps1
3. 依存をインストール:
   pip install -r requirements.txt
4. assets フォルダに background.png, char.png を置く（1280x720 推奨）
5. VOICEVOX Editor を起動（http://127.0.0.1:50021 が生きていることを確認）
6. 実行:
   python generate_yukkuri.py "トピック名"
7. 出力:
   out/result.mp4 が生成されます

注意
- VOICEVOX のスピーカー ID は /speakers を叩いて確認し、スクリプト内の VOICE_ID を調整してください。
- 外部素材（BGM、立ち絵等）は利用許可を必ず確認してください。

次のステップの提案
- README をより詳細に整備（使い方、スピーカーIDの確認方法、よくあるエラー）
- GitHub Pages にデモやドキュメントを公開
- Issue テンプレート・CONTRIBUTING を追加して外注やコントリビュートを受けられる体制にする
