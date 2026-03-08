import os, requests
from datetime import date, timedelta


def _get_slack_user_id() -> str:
    token = os.environ.get("SLACK_BOT_TOKEN")
    email = os.environ.get("SLACK_USER_EMAIL")
    if not token:
        return ""
    if email:
        res = requests.get(
            "https://slack.com/api/users.lookupByEmail",
            headers={"Authorization": f"Bearer {token}"},
            params={"email": email},
        )
        data = res.json()
        if data.get("ok"):
            return data["user"]["id"]
    # メールなしの場合はauth.testでBotのUser IDを取得
    res = requests.post(
        "https://slack.com/api/auth.test",
        headers={"Authorization": f"Bearer {token}"},
    )
    return res.json().get("user_id", "")


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
    user_id = _get_slack_user_id()
    mention = f"<@{user_id}> " if user_id else ""

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
                    "text": f"{mention}Powered by Fitbit API × Claude API × GitHub Actions",
                }
            ],
        },
    ]

    res = requests.post(webhook_url, json={"blocks": blocks})
    res.raise_for_status()
    print("✅ Slack投稿完了")


def post_weekly_report(weekly_data, ai_comment):
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    sleep = weekly_data["sleep"]
    steps = weekly_data["steps"]
    heart = weekly_data["heart"]
    user_id = _get_slack_user_id()
    mention = f"<@{user_id}> " if user_id else ""

    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=6)
    period = f"{start.strftime('%m/%d')}〜{end.strftime('%m/%d')}"

    avg_h = sleep["avg_minutes"] // 60
    avg_m = sleep["avg_minutes"] % 60

    sleep_daily_text = " ｜ ".join(
        f"{d['day']} {d['total_minutes'] // 60}h{d['total_minutes'] % 60:02d}m"
        for d in sleep["daily"]
    )

    steps_daily_text = " ｜ ".join(
        f"{d['day']} {d['steps']:,}" for d in steps["daily"]
    )

    advice_text = "\n".join(f"• {a}" for a in ai_comment.get("advice", []))

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📊 Weekly Health Summary — {period}",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*😴 睡眠（7日間平均）*\n"
                    f"睡眠時間: *{avg_h}時間{avg_m}分* ｜ 効率: *{sleep['avg_efficiency']}%*\n\n"
                    f"{sleep_daily_text}"
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
                        f"*🚶 アクティビティ（7日間）*\n"
                        f"平均歩数: *{steps['avg_steps']:,}歩/日*\n"
                        f"合計歩数: *{steps['total_steps']:,}歩*\n"
                        f"平均カロリー: *{steps['avg_calories']:,}kcal/日*"
                    ),
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        f"*❤️ 心拍（7日間平均）*\n"
                        f"安静時心拍: *{heart['avg_resting_heart_rate']}bpm*\n"
                        f"HRV (RMSSD): *{heart['avg_hrv']}ms*"
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
                    f"*🤖 週間レビュー*\n"
                    f"{ai_comment.get('review', '')}\n\n"
                    f"*💡 来週のアドバイス*\n{advice_text}"
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"{mention}Powered by Fitbit API × Claude API × GitHub Actions",
                }
            ],
        },
    ]

    res = requests.post(webhook_url, json={"blocks": blocks})
    res.raise_for_status()
    print("✅ 週次レポート投稿完了")
