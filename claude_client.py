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


def generate_health_comment(health_data):
    sleep, steps, heart = (
        health_data["sleep"],
        health_data["steps"],
        health_data["heart"],
    )
    prompt = f"""以下のFitbitデータを分析し、JSON形式のみで返してください。余計な説明は不要です。
睡眠効率:{sleep['score']}% 睡眠時間:{sleep['total_minutes']}分
深睡眠:{sleep['deep_minutes']}分 REM:{sleep['rem_minutes']}分
歩数:{steps['steps']}歩 消費:{steps['calories']}kcal
安静時心拍:{heart['resting_heart_rate']}bpm HRV:{heart['hrv']}ms

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
