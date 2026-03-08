import os, json, re, requests


def _extract_json(text):
    """レスポンスからJSON部分を抽出する"""
    # ```json ... ``` ブロックがあればその中身を取得
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # { ... } を直接探す
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise ValueError(f"JSONが見つかりません: {text[:200]}")


def generate_health_comment(health_data, work_style_context=None):
    sleep, steps, heart = (
        health_data["sleep"],
        health_data["steps"],
        health_data["heart"],
    )

    # 勤務形態に応じたコンテキスト
    work_context = ""
    if work_style_context:
        if work_style_context.get("is_remote"):
            work_context = """
【勤務形態】在宅勤務
※在宅勤務のため、通勤がありません。室内でできる運動や、意識的に外出する提案をしてください。
"""
        else:
            work_context = """
【勤務形態】出社勤務
※通勤があるため、通勤時間を活用した運動の提案が可能です。
"""

    prompt = f"""以下のFitbitデータを分析し、JSON形式のみで返してください。余計な説明は不要です。
睡眠効率:{sleep['score']}% 睡眠時間:{sleep['total_minutes']}分
深睡眠:{sleep['deep_minutes']}分 REM:{sleep['rem_minutes']}分
歩数:{steps['steps']}歩 消費:{steps['calories']}kcal
安静時心拍:{heart['resting_heart_rate']}bpm HRV:{heart['hrv']}ms
{work_context}
{{"condition": "今日の体の状態を2〜3文で", "actions": ["提案1", "提案2", "提案3"]}}"""

    res = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 512,
            "system": "健康データを分析するパーソナルコーチです。日本語で回答します。JSONのみ返してください。",
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    res.raise_for_status()
    text = res.json()["content"][0]["text"].strip()
    return _extract_json(text)


def generate_weekly_comment(weekly_data, work_style_context=None):
    sleep = weekly_data["sleep"]
    steps = weekly_data["steps"]
    heart = weekly_data["heart"]
    sleep_daily = " / ".join(
        f"{d['day']}:{d['total_minutes']}分" for d in sleep["daily"]
    )
    steps_daily = " / ".join(
        f"{d['day']}:{d['steps']}歩" for d in steps["daily"]
    )

    # 勤務形態に応じたコンテキスト
    work_context = ""
    if work_style_context:
        style = work_style_context.get("work_style", "office")
        if style == "remote":
            work_context = """
【勤務形態】在宅勤務
※在宅勤務のため、通勤がありません。室内でできる運動や、意識的に外出する提案をしてください。「一駅歩く」などの通勤を前提としたアドバイスは避けてください。
"""
        elif style == "hybrid":
            remote_days = work_style_context.get("remote_days", [])
            days_str = "・".join(remote_days) if remote_days else "なし"
            work_context = f"""
【勤務形態】ハイブリッド勤務（在宅: {days_str}）
※在宅日と出社日でアドバイスを使い分けてください。在宅日は室内運動を、出社日は通勤活用を提案してください。
"""
        else:
            work_context = """
【勤務形態】出社勤務
※通勤があるため、通勤時間を活用した運動の提案が可能です。
"""

    prompt = f"""以下の1週間のFitbitデータを分析し、JSON形式のみで返してください。余計な説明は不要です。

【睡眠】平均:{sleep['avg_minutes']}分 効率:{sleep['avg_efficiency']}%
日別: {sleep_daily}
【歩数】平均:{steps['avg_steps']}歩/日 合計:{steps['total_steps']}歩
日別: {steps_daily}
【心拍】安静時心拍平均:{heart['avg_resting_heart_rate']}bpm HRV平均:{heart['avg_hrv']}ms
{work_context}
{{"review": "1週間の振り返りを3〜4文で", "advice": ["来週のアドバイス1", "来週のアドバイス2", "来週のアドバイス3"]}}"""

    res = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 512,
            "system": "健康データを分析するパーソナルコーチです。日本語で回答します。JSONのみ返してください。",
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    res.raise_for_status()
    text = res.json()["content"][0]["text"].strip()
    return _extract_json(text)
