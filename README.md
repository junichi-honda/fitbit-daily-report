# Fitbit Daily Health Report Bot

Fitbit のデータを自動取得し、Claude AI の分析コメント付きで Slack に投稿する GitHub Actions Bot。

- **朝レポート**: 睡眠データを毎朝9時（JST）に投稿
- **夜レポート**: 活動データを毎夜21時（JST）に投稿
- **週次サマリー**: 毎週日曜日の夜に7日間の集計を投稿
- **月次サマリー**: 毎月1日の夜に前月の集計＋先月比を投稿

## クイックスタート

このリポジトリはテンプレートとして公開されています。以下の手順で自分用にコピーできます：

1. 画面右上の **「Use this template」** ボタンをクリック
2. **「Create a new repository」** を選択
3. リポジトリ名を入力して作成（例: `my-fitbit-report`）
4. 作成されたリポジトリで「[セットアップ](#セットアップ)」の手順に従って各種 API キーを設定

> **Note**: Fork ではなく「Use this template」を使うことで、コミット履歴のないクリーンな状態から始められます。

## 構成

```
├── .github/workflows/daily_report.yml  # 定時実行（朝9時・夜21時 JST）
├── main.py                              # エントリーポイント
├── fitbit_client.py                     # Fitbit API・認証処理
├── token_manager.py                     # リフレッシュトークン自動更新
├── claude_client.py                     # Claude APIコメント生成
├── slack_notifier.py                    # Slack Block Kit投稿
└── requirements.txt
```

## 処理フロー

1. Fitbit API でトークンをリフレッシュ
2. 新しいリフレッシュトークンを GitHub Secret に自動保存
3. 睡眠・歩数・心拍データを取得
4. Claude API でデータを分析し健康コメントを生成
5. Slack に Block Kit 形式でレポート投稿
6. 日曜日の夜: 週次サマリーを追加投稿
7. 毎月1日の夜: 月次サマリーを追加投稿（先月比付き）

## レポート内容

### 朝レポート（毎日 9:00 JST）
- **睡眠**: 睡眠時間、効率、深い睡眠/REM/浅い睡眠/覚醒の内訳
- **AIコーチ**: 睡眠の質の分析と今日のコンディションに合わせた提案

### 夜レポート（毎日 21:00 JST）
- **アクティビティ**: 歩数（目標10,000歩対比）、消費カロリー
- **心拍**: 安静時心拍数、HRV (RMSSD)
- **AIコーチ**: 活動量の分析と明日に向けた提案

### 週次サマリー（毎週日曜日 21:00 JST）
- 7日間の睡眠・歩数・心拍の日別推移と平均
- AIによる週間レビューと来週のアドバイス

### 月次サマリー（毎月1日 21:00 JST）
- 前月の睡眠・歩数・心拍の月間平均
- **先月比較**: 各指標の前月差を↑↓で表示
- AIによる月間レビューと来月のアドバイス

## セットアップ

### 1. Fitbit アプリ登録

[dev.fitbit.com](https://dev.fitbit.com/apps) でアプリを作成し、以下を取得:

- OAuth 2.0 Client ID
- Client Secret
- Redirect URL: `http://localhost:8080/callback`

### 2. 初回リフレッシュトークン取得

ブラウザで認可URL を開く（`YOUR_CLIENT_ID` を置換）:

```
https://www.fitbit.com/oauth2/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:8080/callback&scope=activity+heartrate+sleep&expires_in=604800
```

許可後、URLバーの `code=` の値をコピーし、すぐに以下を実行:

```bash
curl -X POST https://api.fitbit.com/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -u "YOUR_CLIENT_ID:YOUR_CLIENT_SECRET" \
  -d "grant_type=authorization_code&code=取得したCODE&redirect_uri=http://localhost:8080/callback"
```

レスポンスの `refresh_token` を控える。

### 3. 各種 API キーの取得

#### ANTHROPIC_API_KEY（Claude API キー）

1. [console.anthropic.com](https://console.anthropic.com/) にログイン
2. Settings > API Keys を開く
3. 「Create Key」でキーを生成しコピー

#### SLACK_WEBHOOK_URL（Slack Incoming Webhook URL）

1. [api.slack.com/apps](https://api.slack.com/apps) にアクセス
2. 対象のアプリを選択（または「Create New App」で新規作成）
3. 左メニュー「Incoming Webhooks」を開き、有効化
4. 「Add New Webhook to Workspace」で投稿先チャンネルを選択
5. 生成された `https://hooks.slack.com/services/...` の URL をコピー

#### GH_PAT（GitHub Personal Access Token）

1. GitHub にログインし、Settings > Developer settings > [Personal access tokens > Tokens (classic)](https://github.com/settings/tokens) を開く
2. 「Generate new token (classic)」をクリック
3. スコープは **`repo`** にチェック（Secret の読み書きに必要）
4. 生成されたトークンをコピー

### 4. GitHub 設定

**Secrets** (Settings > Secrets and variables > Actions > Repository secrets):

| Name | 値 |
|---|---|
| `FITBIT_CLIENT_SECRET` | Fitbit Client Secret |
| `FITBIT_REFRESH_TOKEN` | 取得した refresh_token |
| `ANTHROPIC_API_KEY` | Claude API キー |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |
| `GH_PAT` | GitHub Personal Access Token |

**Variables** (Settings > Secrets and variables > Actions > Variables):

| Name | 値 |
|---|---|
| `FITBIT_CLIENT_ID` | Fitbit Client ID |

### 5. 動作確認

Actions タブから「Daily Health Report」を手動実行（Run workflow）して Slack への投稿を確認。

## 投稿サンプル

**朝レポート**
```
🌅 Morning Report — XXXX/XX/XX

😴 昨夜の睡眠
睡眠時間: X時間XX分 ｜ 効率: XX%
深い睡眠: XX分 ██░░░░░░░░
REM睡眠: XX分 █░░░░░░░░░
浅い睡眠: XXX分 ██████░░░░
覚醒: XX分 ██░░░░░░░░

🤖 AIコーチからのコメント
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

💡 今日のアクション
• XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
• XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
• XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**夜レポート**
```
🌙 Evening Report — XXXX/XX/XX

🚶 アクティビティ          ❤️ 心拍
歩数: X,XXX歩              安静時心拍: XXbpm
███░░░░░░░ (XX%)           HRV (RMSSD): XX.Xms
消費カロリー: X,XXXkcal

🤖 AIコーチからのコメント
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

💡 明日のアクション
• XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**週次サマリー（日曜日）**
```
📊 Weekly Health Summary — XX/XX〜XX/XX

😴 睡眠（7日間平均）
睡眠時間: X時間XX分 ｜ 効率: XX%
月 X時間XX分 ｜ 火 X時間XX分 ｜ ...

🚶 アクティビティ          ❤️ 心拍（7日間平均）
平均歩数: X,XXX歩/日       安静時心拍: XXbpm
合計歩数: XX,XXX歩         HRV: XX.Xms
平均カロリー: X,XXXkcal/日

🤖 週間レビュー / 💡 来週のアドバイス
```

**月次サマリー（毎月1日）**
```
📅 Monthly Health Summary — XXXX年X月

😴 睡眠（月間平均）
睡眠時間: X時間XX分 ↑XX分 ｜ 効率: XX% ↑X%
先月: X時間XX分 / XX%

🚶 アクティビティ（月間）  ❤️ 心拍（月間平均）
平均歩数: X,XXX歩/日 ↑XX  安静時心拍: XXbpm ↓X
合計歩数: XXX,XXX歩 ↑XXX  HRV: XX.Xms ↑X.X
先月: X,XXX歩/日           先月: XXbpm / XX.Xms

🤖 月間レビュー / 💡 来月のアドバイス
```

## コスト

ほぼ無料（Claude API 約 ¥30〜40/月のみ）

## 技術スタック

- **Fitbit Web API** — 健康データ取得
- **Claude API** (claude-sonnet-4-5) — AI 分析コメント
- **Slack Incoming Webhooks** — Block Kit レポート投稿
- **GitHub Actions** — 定時実行 & トークン自動管理

## ライセンス

[MIT License](LICENSE)
