import os, sys, traceback, requests
from fitbit_client import FitbitClient
from token_manager import update_github_secret
from claude_client import generate_health_comment
from slack_notifier import post_health_report


def notify_error(message):
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return
    try:
        requests.post(webhook_url, json={"text": f":warning: *エラー発生*\n```{message}```"})
    except Exception:
        pass


def main():
    required = [
        "FITBIT_CLIENT_ID",
        "FITBIT_CLIENT_SECRET",
        "FITBIT_REFRESH_TOKEN",
        "ANTHROPIC_API_KEY",
        "SLACK_WEBHOOK_URL",
        "GH_PAT",
        "GH_REPO_OWNER",
        "GH_REPO_NAME",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f":x: 環境変数不足: {missing}")
        sys.exit(1)

    client = FitbitClient(
        os.environ["FITBIT_CLIENT_ID"],
        os.environ["FITBIT_CLIENT_SECRET"],
        os.environ["FITBIT_REFRESH_TOKEN"],
    )

    try:
        new_token = client.refresh_access_token()
    except Exception as e:
        notify_error(f"トークンリフレッシュ失敗: {e}")
        sys.exit(1)

    try:
        update_github_secret(new_token)
    except Exception as e:
        notify_error(f"Secret更新失敗: {e}")
        sys.exit(1)

    try:
        health_data = {
            "sleep": client.get_sleep(),
            "steps": client.get_steps(),
            "heart": client.get_heart_rate(),
        }
    except Exception as e:
        notify_error(f"データ取得失敗: {e}")
        sys.exit(1)

    try:
        ai_comment = generate_health_comment(health_data)
    except Exception as e:
        print(f":warning: Claude APIエラー: {e}")
        ai_comment = {"condition": "AIコメント生成失敗", "actions": ["水分補給を忘れずに"]}

    try:
        post_health_report(health_data, ai_comment)
    except Exception as e:
        notify_error(f"Slack投稿失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
