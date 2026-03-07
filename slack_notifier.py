import os, requests
from datetime import date, timedelta


def _format_sleep_bar(minutes, total_minutes):
    if total_minutes == 0:
        return ""
    ratio = min(minutes / total_minutes, 1.0)
    filled = round(ratio * 10)
    return "█" * filled + "░" * (10 - filled)


def _format_steps_bar(steps, goal=10000):
    ratio = min(steps / goal, 1.0)
    filled = round(ratio * 10)
    return "█" * filled + "░" * (10 - filled)


def post_health_report(health_data, ai_comment):
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    sleep = health_data["sleep"]
    steps = health_data["steps"]
    heart = health_data["heart"]
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y/%m/%d")

    total_h = sleep["total_minutes"] // 60
    total_m = sleep["total_minutes"] % 60

    actions_text = "\n".join(f"• {a}" for a in ai_comment.get("actions", []))

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🏃 Daily Health Report — {yesterday}",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*😴 睡眠*\n"
                    f"睡眠時間: *{total_h}時間{total_m}分* ｜ 効率: *{sleep['score']}%*\n"
                    f"深い睡眠: {sleep['deep_minutes']}分 {_format_sleep_bar(sleep['deep_minutes'], sleep['total_minutes'])}\n"
                    f"REM睡眠: {sleep['rem_minutes']}分 {_format_sleep_bar(sleep['rem_minutes'], sleep['total_minutes'])}\n"
                    f"浅い睡眠: {sleep['light_minutes']}分 {_format_sleep_bar(sleep['light_minutes'], sleep['total_minutes'])}\n"
                    f"覚醒: {sleep['awake_minutes']}分 {_format_sleep_bar(sleep['awake_minutes'], sleep['total_minutes'])}"
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"*🚶 アクティビティ*\n"
                        f"歩数: *{steps['steps']:,}歩*\n"
                        f"{_format_steps_bar(steps['steps'])} ({min(steps['steps'] * 100 // 10000, 100)}%)\n"
                        f"消費カロリー: *{steps['calories']:,}kcal*"
                    ),
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        f"*❤️ 心拍*\n"
                        f"安静時心拍: *{heart['resting_heart_rate']}bpm*\n"
                        f"HRV (RMSSD): *{heart['hrv']}ms*"
                    ),
                },
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*🤖 AIコーチからのコメント*\n"
                    f"{ai_comment.get('condition', '')}\n\n"
                    f"*💡 今日のアクション*\n{actions_text}"
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Powered by Fitbit API × Claude API × GitHub Actions",
                }
            ],
        },
    ]

    res = requests.post(webhook_url, json={"blocks": blocks})
    res.raise_for_status()
    print("✅ Slack投稿完了")
