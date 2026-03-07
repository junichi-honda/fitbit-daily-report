import os, sys, traceback, requests
from datetime import date
from fitbit_client import FitbitClient
from token_manager import update_github_secret
from claude_client import generate_health_comment, generate_weekly_comment
from slack_notifier import post_health_report, post_weekly_report


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
        print(f"トークンリフレッシュ失敗: {e}", file=sys.stderr)
        traceback.print_exc()
        notify_error(f"トークンリフレッシュ失敗: {e}")
        sys.exit(1)

    try:
        update_github_secret(new_token)
    except Exception as e:
        print(f"Secret更新失敗: {e}", file=sys.stderr)
        traceback.print_exc()
        notify_error(f"Secret更新失敗: {e}")
        sys.exit(1)

    try:
        health_data = {
            "sleep": client.get_sleep(),
            "steps": client.get_steps(),
            "heart": client.get_heart_rate(),
        }
    except Exception as e:
        print(f"データ取得失敗: {e}", file=sys.stderr)
        traceback.print_exc()
        notify_error(f"データ取得失敗: {e}")
        sys.exit(1)

    try:
        ai_comment = generate_health_comment(health_data)
    except Exception as e:
        print(f"Claude APIエラー: {e}", file=sys.stderr)
        traceback.print_exc()
        ai_comment = {"condition": "AIコメント生成失敗", "actions": ["水分補給を忘れずに"]}

    try:
        post_health_report(health_data, ai_comment)
    except Exception as e:
        print(f"Slack投稿失敗: {e}", file=sys.stderr)
        traceback.print_exc()
        notify_error(f"Slack投稿失敗: {e}")
        sys.exit(1)

    # 日曜日は週次サマリーも投稿
    if date.today().weekday() == 6:
        print("📊 日曜日のため週次サマリーを生成します")
        try:
            weekly_data = {
                "sleep": client.get_weekly_sleep(),
                "steps": client.get_weekly_steps(),
                "heart": client.get_weekly_heart_rate(),
            }
        except Exception as e:
            print(f"週次データ取得失敗: {e}", file=sys.stderr)
            traceback.print_exc()
            notify_error(f"週次データ取得失敗: {e}")
            sys.exit(1)

        try:
            weekly_comment = generate_weekly_comment(weekly_data)
        except Exception as e:
            print(f"週次Claude APIエラー: {e}", file=sys.stderr)
            traceback.print_exc()
            weekly_comment = {
                "review": "週次レビュー生成失敗",
                "advice": ["規則正しい生活を心がけましょう"],
            }

        try:
            post_weekly_report(weekly_data, weekly_comment)
        except Exception as e:
            print(f"週次Slack投稿失敗: {e}", file=sys.stderr)
            traceback.print_exc()
            notify_error(f"週次Slack投稿失敗: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
