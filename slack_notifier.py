import os, requests
from datetime import date, timedelta
from config import DAILY_STEP_GOAL


def _get_slack_user_id() -> str:
    return os.environ.get("SLACK_USER_ID", "")


def _today() -> str:
    return date.today().strftime("%Y/%m/%d")


def _format_sleep_bar(minutes, total_minutes):
    if total_minutes == 0:
        return ""
    ratio = min(minutes / total_minutes, 1.0)
    filled = round(ratio * 10)
    return "█" * filled + "░" * (10 - filled)


def _format_steps_bar(steps, goal=DAILY_STEP_GOAL):
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
                        f"{_format_steps_bar(steps['steps'])} ({min(steps['steps'] * 100 // DAILY_STEP_GOAL, 100)}%)\n"
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


def post_morning_report(sleep_data):
    """朝の睡眠レポートを投稿"""
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    today = _today()
    user_id = _get_slack_user_id()
    mention = f"<@{user_id}> " if user_id else ""

    total_h = sleep_data["total_minutes"] // 60
    total_m = sleep_data["total_minutes"] % 60

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🌅 Morning Sleep Report — {today}",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*😴 昨夜の睡眠*\n"
                    f"睡眠時間: *{total_h}時間{total_m}分* ｜ 効率: *{sleep_data['score']}%*\n"
                    f"深い睡眠: {sleep_data['deep_minutes']}分 {_format_sleep_bar(sleep_data['deep_minutes'], sleep_data['total_minutes'])}\n"
                    f"REM睡眠: {sleep_data['rem_minutes']}分 {_format_sleep_bar(sleep_data['rem_minutes'], sleep_data['total_minutes'])}\n"
                    f"浅い睡眠: {sleep_data['light_minutes']}分 {_format_sleep_bar(sleep_data['light_minutes'], sleep_data['total_minutes'])}\n"
                    f"覚醒: {sleep_data['awake_minutes']}分 {_format_sleep_bar(sleep_data['awake_minutes'], sleep_data['total_minutes'])}"
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"{mention}Powered by Fitbit API × GitHub Actions",
                }
            ],
        },
    ]

    res = requests.post(webhook_url, json={"blocks": blocks})
    res.raise_for_status()
    print("✅ 朝のレポート投稿完了")


def post_evening_report(steps_data, heart_data):
    """夜のアクティビティレポートを投稿"""
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    today = _today()
    user_id = _get_slack_user_id()
    mention = f"<@{user_id}> " if user_id else ""

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🌙 Evening Activity Report — {today}",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"*🚶 今日のアクティビティ*\n"
                        f"歩数: *{steps_data['steps']:,}歩*\n"
                        f"{_format_steps_bar(steps_data['steps'])} ({min(steps_data['steps'] * 100 // DAILY_STEP_GOAL, 100)}%)\n"
                        f"消費カロリー: *{steps_data['calories']:,}kcal*"
                    ),
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        f"*❤️ 心拍*\n"
                        f"安静時心拍: *{heart_data['resting_heart_rate']}bpm*\n"
                        f"HRV (RMSSD): *{heart_data['hrv']}ms*"
                    ),
                },
            ],
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"{mention}Powered by Fitbit API × GitHub Actions",
                }
            ],
        },
    ]

    res = requests.post(webhook_url, json={"blocks": blocks})
    res.raise_for_status()
    print("✅ 夜のレポート投稿完了")


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


def post_monthly_report(monthly_data, ai_comment):
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    sleep = monthly_data["sleep"]
    steps = monthly_data["steps"]
    heart = monthly_data["heart"]
    user_id = _get_slack_user_id()
    mention = f"<@{user_id}> " if user_id else ""

    today = date.today()
    year = today.year
    month = today.month - 1 or 12
    if today.month == 1:
        year -= 1

    def _arrow(current, last):
        if current == "N/A" or last == "N/A":
            return "–"
        diff = current - last
        if diff > 0:
            return f"↑{abs(diff)}"
        elif diff < 0:
            return f"↓{abs(diff)}"
        return "→0"

    avg_h = sleep["avg_minutes"] // 60
    avg_m = sleep["avg_minutes"] % 60
    sleep_diff_min = _arrow(sleep["avg_minutes"], sleep["last_avg_minutes"])
    sleep_diff_eff = _arrow(sleep["avg_efficiency"], sleep["last_avg_efficiency"])

    steps_diff_total = _arrow(steps["total_steps"], steps["last_total_steps"])
    steps_diff_avg = _arrow(steps["avg_steps"], steps["last_avg_steps"])

    rhr_diff = _arrow(
        heart["avg_resting_heart_rate"] if heart["avg_resting_heart_rate"] != "N/A" else "N/A",
        heart["last_avg_resting_heart_rate"] if heart["last_avg_resting_heart_rate"] != "N/A" else "N/A",
    )
    hrv_diff = _arrow(
        heart["avg_hrv"] if heart["avg_hrv"] != "N/A" else "N/A",
        heart["last_avg_hrv"] if heart["last_avg_hrv"] != "N/A" else "N/A",
    )

    advice_text = "\n".join(f"• {a}" for a in ai_comment.get("advice", []))

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📅 月次ヘルスレポート {year}年{month}月",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*😴 睡眠（今月平均）*\n"
                    f"睡眠時間: *{avg_h}時間{avg_m}分* （先月比: {sleep_diff_min}分）\n"
                    f"効率: *{sleep['avg_efficiency']}%* （先月比: {sleep_diff_eff}%）"
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
                        f"*🚶 アクティビティ（今月）*\n"
                        f"合計歩数: *{steps['total_steps']:,}歩* （先月比: {steps_diff_total}）\n"
                        f"平均歩数: *{steps['avg_steps']:,}歩/日* （先月比: {steps_diff_avg}）\n"
                        f"平均カロリー: *{steps['avg_calories']:,}kcal/日*"
                    ),
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        f"*❤️ 心拍（今月平均）*\n"
                        f"安静時心拍: *{heart['avg_resting_heart_rate']}bpm* （先月比: {rhr_diff}）\n"
                        f"HRV (RMSSD): *{heart['avg_hrv']}ms* （先月比: {hrv_diff}）"
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
                    f"*🤖 月次レビュー*\n"
                    f"{ai_comment.get('review', '')}\n\n"
                    f"*💡 来月のアドバイス*\n{advice_text}"
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
    print("✅ 月次レポート投稿完了")
