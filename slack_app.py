"""Slack Bolt アプリ - 設定モーダル機能"""
import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from user_settings import load_settings, save_settings, get_work_style_label

# Socket Mode で起動（SLACK_APP_TOKEN と SLACK_BOT_TOKEN が必要）
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))


def build_settings_modal(current_settings: dict) -> dict:
    """設定モーダルのビューを構築"""
    work_style = current_settings.get("work_style", "office")
    remote_days = current_settings.get("remote_days", [])

    # 勤務形態の初期値
    initial_option = {
        "office": {"text": {"type": "plain_text", "text": "出社勤務"}, "value": "office"},
        "remote": {"text": {"type": "plain_text", "text": "在宅勤務"}, "value": "remote"},
        "hybrid": {"text": {"type": "plain_text", "text": "ハイブリッド"}, "value": "hybrid"},
    }.get(work_style, {"text": {"type": "plain_text", "text": "出社勤務"}, "value": "office"})

    # 曜日チェックボックスの初期値
    day_options = [
        {"text": {"type": "plain_text", "text": day}, "value": day}
        for day in ["月", "火", "水", "木", "金"]
    ]
    initial_days = [
        {"text": {"type": "plain_text", "text": day}, "value": day}
        for day in remote_days
        if day in ["月", "火", "水", "木", "金"]
    ]

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*勤務形態を設定*\n在宅勤務の場合、健康アドバイスが勤務スタイルに合わせて最適化されます。",
            },
        },
        {"type": "divider"},
        {
            "type": "input",
            "block_id": "work_style_block",
            "element": {
                "type": "static_select",
                "action_id": "work_style_select",
                "placeholder": {"type": "plain_text", "text": "勤務形態を選択"},
                "initial_option": initial_option,
                "options": [
                    {"text": {"type": "plain_text", "text": "出社勤務"}, "value": "office"},
                    {"text": {"type": "plain_text", "text": "在宅勤務"}, "value": "remote"},
                    {"text": {"type": "plain_text", "text": "ハイブリッド"}, "value": "hybrid"},
                ],
            },
            "label": {"type": "plain_text", "text": "勤務形態"},
        },
        {
            "type": "input",
            "block_id": "remote_days_block",
            "optional": True,
            "element": {
                "type": "checkboxes",
                "action_id": "remote_days_select",
                "options": day_options,
                **({"initial_options": initial_days} if initial_days else {}),
            },
            "label": {"type": "plain_text", "text": "在宅勤務日（ハイブリッドの場合）"},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "💡 ハイブリッド勤務の場合は、在宅勤務の曜日を選択してください。",
                }
            ],
        },
    ]

    return {
        "type": "modal",
        "callback_id": "settings_modal",
        "title": {"type": "plain_text", "text": "勤務設定"},
        "submit": {"type": "plain_text", "text": "保存"},
        "close": {"type": "plain_text", "text": "キャンセル"},
        "blocks": blocks,
    }


@app.command("/settings")
def handle_settings_command(ack, body, client):
    """スラッシュコマンド /settings で設定モーダルを開く"""
    ack()
    current_settings = load_settings()
    client.views_open(
        trigger_id=body["trigger_id"],
        view=build_settings_modal(current_settings),
    )


@app.shortcut("open_settings")
def handle_settings_shortcut(ack, shortcut, client):
    """ショートカットから設定モーダルを開く"""
    ack()
    current_settings = load_settings()
    client.views_open(
        trigger_id=shortcut["trigger_id"],
        view=build_settings_modal(current_settings),
    )


@app.view("settings_modal")
def handle_settings_submission(ack, body, view, client):
    """設定モーダルの送信を処理"""
    ack()

    values = view["state"]["values"]

    work_style = values["work_style_block"]["work_style_select"]["selected_option"]["value"]
    remote_days_selection = values["remote_days_block"]["remote_days_select"].get("selected_options", [])
    remote_days = [opt["value"] for opt in remote_days_selection]

    settings = {
        "work_style": work_style,
        "remote_days": remote_days,
    }
    save_settings(settings)

    # 保存完了メッセージ
    user_id = body["user"]["id"]
    style_label = get_work_style_label(settings)
    client.chat_postMessage(
        channel=user_id,
        text=f"✅ 勤務設定を保存しました！\n現在の設定: *{style_label}*",
    )


@app.event("app_home_opened")
def handle_app_home_opened(client, event):
    """アプリホームを開いたときに設定画面を表示"""
    user_id = event["user"]
    current_settings = load_settings()
    style_label = get_work_style_label(current_settings)

    client.views_publish(
        user_id=user_id,
        view={
            "type": "home",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "Fitbit Daily Report 設定"},
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*現在の勤務設定*\n{style_label}",
                    },
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "設定を変更"},
                        "action_id": "open_settings_button",
                    },
                },
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "💡 `/settings` コマンドでも設定を変更できます。",
                        }
                    ],
                },
            ],
        },
    )


@app.action("open_settings_button")
def handle_open_settings_button(ack, body, client):
    """ホームタブのボタンから設定モーダルを開く"""
    ack()
    current_settings = load_settings()
    client.views_open(
        trigger_id=body["trigger_id"],
        view=build_settings_modal(current_settings),
    )


def start_app():
    """Slack アプリを起動"""
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    print("⚡️ Slack Bolt app is running!")
    handler.start()


if __name__ == "__main__":
    start_app()
