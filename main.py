import os, sys, traceback, requests, argparse
from datetime import date
from fitbit_client import FitbitClient
from token_manager import update_github_secret
from claude_client import (
    generate_health_comment,
    generate_weekly_comment,
    generate_sleep_comment,
    generate_activity_comment,
    generate_monthly_comment,
)
from slack_notifier import (
    post_health_report,
    post_weekly_report,
    post_morning_report,
    post_evening_report,
    post_monthly_report,
)


def notify_error(message):
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return
    try:
        requests.post(webhook_url, json={"text": f":warning: *エラー発生*\n```{message}```"})
    except Exception:
        pass


def run_morning_report(client):
    """朝のレポート: 当日の睡眠データを配信"""
    print("🌅 朝のレポートを生成します（当日の睡眠データ）")
    try:
        sleep_data = client.get_sleep()
    except Exception as e:
        print(f"睡眠データ取得失敗: {e}", file=sys.stderr)
        traceback.print_exc()
        notify_error(f"睡眠データ取得失敗: {e}")
        sys.exit(1)

    try:
        ai_comment = generate_sleep_comment(sleep_data)
    except Exception as e:
        print(f"Claude APIエラー: {e}", file=sys.stderr)
        traceback.print_exc()
        ai_comment = {"condition": "AIコメント生成失敗", "actions": ["良い一日を！"]}

    try:
        post_morning_report(sleep_data, ai_comment)
    except Exception as e:
        print(f"Slack投稿失敗: {e}", file=sys.stderr)
        traceback.print_exc()
        notify_error(f"Slack投稿失敗: {e}")
        sys.exit(1)


def run_monthly_report(client):
    """月次レポート: 今月・先月のデータを比較して配信"""
    print("📅 月次レポートを生成します（今月・先月の比較）")
    try:
        monthly_data = {
            "sleep": client.get_monthly_sleep(),
            "steps": client.get_monthly_steps(),
            "heart": client.get_monthly_heart_rate(),
        }
    except Exception as e:
        print(f"月次データ取得失敗: {e}", file=sys.stderr)
        traceback.print_exc()
        notify_error(f"月次データ取得失敗: {e}")
        sys.exit(1)

    try:
        monthly_comment = generate_monthly_comment(monthly_data)
    except Exception as e:
        print(f"月次Claude APIエラー: {e}", file=sys.stderr)
        traceback.print_exc()
        monthly_comment = {
            "review": "月次レビュー生成失敗",
            "advice": ["規則正しい生活を心がけましょう"],
        }

    try:
        post_monthly_report(monthly_data, monthly_comment)
    except Exception as e:
        print(f"月次Slack投稿失敗: {e}", file=sys.stderr)
        traceback.print_exc()
        notify_error(f"月次Slack投稿失敗: {e}")
        sys.exit(1)


def run_evening_report(client):
    """夜のレポート: 当日のアクティビティを配信"""
    print("🌙 夜のレポートを生成します（当日のアクティビティ）")
    try:
        steps_data = client.get_steps()
        heart_data = client.get_heart_rate()
    except Exception as e:
        print(f"アクティビティデータ取得失敗: {e}", file=sys.stderr)
        traceback.print_exc()
        notify_error(f"アクティビティデータ取得失敗: {e}")
        sys.exit(1)

    try:
        ai_comment = generate_activity_comment(steps_data, heart_data)
    except Exception as e:
        print(f"Claude APIエラー: {e}", file=sys.stderr)
        traceback.print_exc()
        ai_comment = {"condition": "AIコメント生成失敗", "actions": ["ゆっくり休んでください"]}

    try:
        post_evening_report(steps_data, heart_data, ai_comment)
    except Exception as e:
        print(f"Slack投稿失敗: {e}", file=sys.stderr)
        traceback.print_exc()
        notify_error(f"Slack投稿失敗: {e}")
        sys.exit(1)

    # 毎月1日は月次サマリーも投稿
    if date.today().day == 1:
        run_monthly_report(client)

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


def main():
    parser = argparse.ArgumentParser(description="Fitbit Daily Health Report")
    parser.add_argument(
        "--mode",
        choices=["morning", "evening"],
        required=True,
        help="morning: 睡眠データを配信, evening: アクティビティを配信",
    )
    args = parser.parse_args()

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

    if args.mode == "morning":
        run_morning_report(client)
    else:
        run_evening_report(client)


if __name__ == "__main__":
    main()
