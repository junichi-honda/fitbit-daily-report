# Fitbit Daily Health Report Bot

Fitbit のデータを毎朝自動取得し、Claude AI の分析コメント付きで Slack に投稿する GitHub Actions Bot。

## クイックスタート

このリポジトリはテンプレートとして公開されています。以下の手順で自分用にコピーできます：

1. 画面右上の **「Use this template」** ボタンをクリック
2. **「Create a new repository」** を選択
3. リポジトリ名を入力して作成（例: `my-fitbit-report`）
4. 作成されたリポジトリで「[セットアップ](#セットアップ)」の手順に従って各種 API キーを設定

> **Note**: Fork ではなく「Use this template」を使うことで、コミット履歴のないクリーンな状態から始められます。

## 構成

```
├── .github/workflows/daily_report.yml  # 毎朝JST 10:30定時実行
├── main.py                              # エントリーポイント
├── fitbit_client.py                     # Fitbit API・認証処理
├── token_manager.py                     # リフレッシュトークン自動更新
├── claude_client.py                     # Claude APIコメント生成（日次・週次）
├── slack_notifier.py                    # Slack Block Kit投稿（日次・週次）
└── requirements.txt
```

## 処理フロー

1. Fitbit API でトークンをリフレッシュ
2. 新しいリフレッシュトークンを GitHub Secret に自動保存
3. 睡眠・歩数・心拍データを取得
4. Claude API でデータを分析し健康コメントを生成
5. Slack に Block Kit 形式でレポート投稿
6. **（日曜日のみ）** 7日分のデータを集計し週次サマリーを追加投稿

## レポート内容

### 日次レポート（毎朝 JST 10:30）

- **睡眠**: 睡眠時間、効率、深い睡眠/REM/浅い睡眠/覚醒の内訳
- **アクティビティ**: 歩数（目標10,000歩対比）、消費カロリー
- **心拍**: 安静時心拍数、HRV (RMSSD)
- **AIコーチ**: 体調コメントと今日のアクション提案

### 週次サマリー（日曜日のみ追加投稿）

- **睡眠（7日間）**: 平均睡眠時間・効率、日別睡眠時間
- **アクティビティ（7日間）**: 平均/合計歩数、平均消費カロリー
- **心拍（7日間）**: 安静時心拍・HRV の週平均
- **AIコーチ**: 1週間の振り返りと来週のアドバイス

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

### 日次レポート

```
🏃 Daily Health Report — XXXX/XX/XX

😴 睡眠
睡眠時間: X時間XX分 ｜ 効率: XX%
深い睡眠: XX分 ██░░░░░░░░
REM睡眠: XX分 █░░░░░░░░░
浅い睡眠: XXX分 ██████░░░░
覚醒: XX分 ██░░░░░░░░

🚶 アクティビティ
歩数: X,XXX歩
███░░░░░░░ (XX%)
消費カロリー: X,XXXkcal

❤️ 心拍
安静時心拍: XXbpm
HRV (RMSSD): XX.Xms

Powered by Fitbit API × Claude API × GitHub Actions
```

### 週次サマリー（日曜日のみ）

```
📊 Weekly Health Summary — XX/XX〜XX/XX

😴 睡眠（7日間平均）
睡眠時間: X時間XX分 ｜ 効率: XX%

月 Xh00m ｜ 火 Xh00m ｜ 水 Xh00m ｜ 木 Xh00m ｜ 金 Xh00m ｜ 土 Xh00m ｜ 日 Xh00m

🚶 アクティビティ（7日間）
平均歩数: X,XXX歩/日
合計歩数: XX,XXX歩
平均カロリー: X,XXXkcal/日

❤️ 心拍（7日間平均）
安静時心拍: XXbpm
HRV (RMSSD): XX.Xms

🤖 週間レビュー
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

💡 来週のアドバイス
• XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
• XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
• XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

Powered by Fitbit API × Claude API × GitHub Actions
```

## コスト

ほぼ無料（Claude API 約 ¥27/月のみ）

## 技術スタック

- **Fitbit Web API** — 健康データ取得
- **Claude API** (claude-sonnet-4-5) — AI 分析コメント
- **Slack Incoming Webhooks** — Block Kit レポート投稿
- **GitHub Actions** — 定時実行 & トークン自動管理

## ライセンス

[MIT License](LICENSE)
