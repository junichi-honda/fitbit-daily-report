"""ユーザー設定の管理モジュール"""
import json
import os
from pathlib import Path

SETTINGS_FILE = Path(__file__).parent / "user_settings.json"

DEFAULT_SETTINGS = {
    "work_style": "office",  # "office", "remote", "hybrid"
    "remote_days": [],  # 曜日リスト ["月", "火", ...]
}


def load_settings() -> dict:
    """設定ファイルを読み込む"""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
                # デフォルト値でマージ
                return {**DEFAULT_SETTINGS, **settings}
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> None:
    """設定をファイルに保存する"""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def get_work_style_label(settings: dict) -> str:
    """現在の勤務形態をラベルとして取得"""
    style = settings.get("work_style", "office")
    labels = {
        "office": "出社勤務",
        "remote": "在宅勤務",
        "hybrid": "ハイブリッド勤務",
    }
    label = labels.get(style, "出社勤務")

    if style == "hybrid" and settings.get("remote_days"):
        days = "・".join(settings["remote_days"])
        label += f"（在宅: {days}）"

    return label


def is_remote_today(settings: dict) -> bool:
    """今日が在宅勤務日かどうかを判定"""
    from datetime import date

    style = settings.get("work_style", "office")

    if style == "remote":
        return True
    elif style == "office":
        return False
    elif style == "hybrid":
        weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
        today_name = weekday_names[date.today().weekday()]
        return today_name in settings.get("remote_days", [])

    return False
