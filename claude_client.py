import os, json, re, requests
from config import (
    ANTHROPIC_API_URL,
    ANTHROPIC_API_VERSION,
    CLAUDE_MODEL,
    CLAUDE_MAX_TOKENS,
    DAILY_STEP_GOAL,
    MIDDAY_STEP_GOAL,
    EOD_STEP_WARN,
)


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


def generate_weekly_comment(weekly_data):
    sleep = weekly_data["sleep"]
    steps = weekly_data["steps"]
    heart = weekly_data["heart"]
    sleep_daily = " / ".join(
        f"{d['day']}:{d['total_minutes']}分" for d in sleep["daily"]
    )
    steps_daily = " / ".join(
        f"{d['day']}:{d['steps']}歩" for d in steps["daily"]
    )
    prompt = f"""以下の1週間のFitbitデータを分析し、JSON形式のみで返してください。余計な説明は不要です。

【睡眠】平均:{sleep['avg_minutes']}分 効率:{sleep['avg_efficiency']}%
日別: {sleep_daily}
【歩数】平均:{steps['avg_steps']}歩/日 合計:{steps['total_steps']}歩
日別: {steps_daily}
【心拍】安静時心拍平均:{heart['avg_resting_heart_rate']}bpm HRV平均:{heart['avg_hrv']}ms

{{"review": "1週間の振り返りを1〜2文で", "advice": ["来週のアドバイス1", "来週のアドバイス2"]}}"""

    res = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": ANTHROPIC_API_VERSION,
            "content-type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": CLAUDE_MAX_TOKENS,
            "system": "健康データを分析するパーソナルコーチです。日本語で回答します。JSONのみ返してください。",
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    res.raise_for_status()
    text = res.json()["content"][0]["text"].strip()
    return _extract_json(text)


def generate_monthly_comment(monthly_data):
    sleep = monthly_data["sleep"]
    steps = monthly_data["steps"]
    heart = monthly_data["heart"]
    prompt = f"""以下の今月と先月のFitbitデータを分析し、JSON形式のみで返してください。余計な説明は不要です。

【睡眠】今月平均:{sleep['avg_minutes']}分 効率:{sleep['avg_efficiency']}% ／ 先月平均:{sleep['last_avg_minutes']}分 効率:{sleep['last_avg_efficiency']}%
【歩数】今月合計:{steps['total_steps']}歩 平均:{steps['avg_steps']}歩/日 ／ 先月合計:{steps['last_total_steps']}歩 平均:{steps['last_avg_steps']}歩/日
【心拍】今月安静時心拍平均:{heart['avg_resting_heart_rate']}bpm HRV平均:{heart['avg_hrv']}ms ／ 先月:{heart['last_avg_resting_heart_rate']}bpm HRV:{heart['last_avg_hrv']}ms

{{"review": "今月の健康状態と先月との比較を1〜2文で", "advice": ["来月のアドバイス1", "来月のアドバイス2"]}}"""

    res = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": ANTHROPIC_API_VERSION,
            "content-type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": CLAUDE_MAX_TOKENS,
            "system": "健康データを分析するパーソナルコーチです。日本語で回答します。JSONのみ返してください。",
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    res.raise_for_status()
    text = res.json()["content"][0]["text"].strip()
    return _extract_json(text)


def generate_step_alert(steps: int, alert_type: str) -> str:
    remaining = max(0, DAILY_STEP_GOAL - steps)
    progress_pct = min(100, int(steps / DAILY_STEP_GOAL * 100))

    if alert_type == "midday":
        timing_desc = "お昼休み前（12:00）"
        situation = (
            f"現在歩数: {steps:,}歩（目標{DAILY_STEP_GOAL:,}歩の{progress_pct}%）\n"
            f"残り: {remaining:,}歩\n"
            + ("午前中はあまり動けていない状況です。" if steps < MIDDAY_STEP_GOAL else "午前中はそこそこ動けています。")
        )
        action_hint = (
            "昼休みに近所を一周する、コンビニまで歩くなど具体的な行動を1つ提案してください。"
            if steps < MIDDAY_STEP_GOAL
            else "このままのペースを維持しつつ、昼休みに軽く外に出ることを勧めてください。"
        )
    else:
        timing_desc = "就業終了前（17:00）"
        situation = (
            f"現在歩数: {steps:,}歩（目標{DAILY_STEP_GOAL:,}歩の{progress_pct}%）\n"
            f"残り: {remaining:,}歩\n"
            + ("今日はかなり歩数が少ない状況です。" if steps < EOD_STEP_WARN else "今日はまずまずのペースです。")
        )
        action_hint = "仕事終わりに取り入れやすい、5〜15分程度の具体的な行動を1つ提案してください。"

    prompt = f"""あなたはフレンドリーな健康習慣コーチです。
以下の状況をもとに、Slackに送る短いメッセージを日本語で書いてください。

タイミング: {timing_desc}
{situation}

ルール:
- 全体を200文字以内に収める
- 責めるトーンは使わない。事実ベースで淡々と、でも温かく
- 絵文字を1〜2個だけ使う
- {action_hint}
- 「今日の目標: {DAILY_STEP_GOAL:,}歩」は必ず含める
- 運動したくなるような座右の銘を1つ添える（有名人の言葉・ことわざなど、毎回異なるものを選ぶ）
"""

    res = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": ANTHROPIC_API_VERSION,
            "content-type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": 300,
            "system": "フレンドリーな健康習慣コーチです。日本語で回答します。",
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    res.raise_for_status()
    return res.json()["content"][0]["text"].strip()
