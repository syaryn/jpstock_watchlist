# jpstock-watchlist

日本株ウォッチリストをスコアリング付きで生成する、PEP8準拠・型安全なPythonプロジェクトです。mise/uv/ruff/pyright/lefthook で品質を自動担保します。

## 主な機能
- Yahoo Finance (yfinance) からリアルタイム株価データを取得
- ROE / EPS成長率 / 予想PER / PBR / 配当利回りを用いた投資スコア算出
- `output/YYYYMMDD.md` に日本語のMarkdown表を日次出力
- `.env` の `TICKERS` で銘柄を簡単に切り替え
- Pydantic + Pyright による型安全なデータ処理
- ruff / lefthook によるPEP8準拠と自動チェック

## 必要ツール
- [mise](https://mise.jdx.dev/)（Pythonや開発ツールの管理）
- Python 3.13+（miseがインストール）

## セットアップ
1. mise をインストール（未導入の場合）
   ```bash
   curl https://mise.run | sh
   ```
2. 開発ツールをインストール
   ```bash
   mise install
   ```
3. 依存関係をインストール（uvが自動でvenv作成）
   ```bash
   uv sync
   ```
4. Gitフックを設定
   ```bash
   lefthook install
   ```
5. 仮想環境を有効化
   ```bash
   source .venv/bin/activate
   ```
6. 銘柄を設定
   ```bash
   cp .env.example .env
   # 例: TICKERS=7203.T,6861.T,8035.T
   ```

## 使い方
```bash
source .venv/bin/activate
mise exec -- python main.py   # .env を自動読込（mise設定）
# もしくは環境変数を直接渡す場合: TICKERS=7203.T,6861.T python main.py
```
実行すると環境変数 `TICKERS` の銘柄を取得し、スコア計算後に `output/YYYYMMDD.md` へMarkdown表を出力します。

### 出力カラム
- ティッカー / 銘柄 / 現在値 / 前日比% / ROE / EPS成長 / 予想PER / PBR / 配当% / スコア（降順ソート）

### スコアリング基準（100点満点）
- ROE: >15% → 30点, >10% → 20点
- EPS成長: >20% → 25点, >0% → 15点
- 予想PER: <15 → 20点, <20 → 10点
- PBR: <1.5 → 15点
- 配当利回り: >3% → 10点

## 開発フローと品質チェック
コミット前に以下が通ることを推奨（lefthookが自動実行）：
```bash
ruff format .        # フォーマット
ruff check --fix .   # リント & 自動修正
pyright              # 型チェック（strict）
pytest               # テスト
```

## プロジェクト構成
```
jpstock_watchlist/
├── main.py                     # エントリーポイント
├── src/jpstock_watchlist/
│   ├── __init__.py
│   ├── models.py               # Pydanticデータモデル
│   ├── fetcher.py              # yfinance連携 & スコア計算
│   └── formatter.py            # Markdown出力
├── output/                     # 生成されるレポート
├── tests/                      # テスト
├── pyproject.toml              # 依存・ツール設定
├── pyrightconfig.json          # 型チェック設定
├── lefthook.yml                # Gitフック
├── mise.toml                   # ツールバージョン & .env読込
└── .env.example                # 銘柄設定テンプレート
```

## 主要ランタイム依存
- yfinance, pandas, tabulate, pydantic

## ライセンス
[Add your license here]
