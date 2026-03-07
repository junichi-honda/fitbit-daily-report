import requests
from datetime import date, timedelta


class FitbitClient:
    BASE_URL = "https://api.fitbit.com/1/user/-"
    AUTH_URL = "https://api.fitbit.com/oauth2/token"

    def __init__(self, client_id, client_secret, refresh_token):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access_token = None

    def refresh_access_token(self):
        res = requests.post(
            self.AUTH_URL,
            data={"grant_type": "refresh_token", "refresh_token": self.refresh_token},
            auth=(self.client_id, self.client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        res.raise_for_status()
        data = res.json()
        self.access_token = data["access_token"]
        return data["refresh_token"]

    def _headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    def _yesterday(self):
        return (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    def get_sleep(self):
        res = requests.get(
            f"{self.BASE_URL}/sleep/date/{self._yesterday()}.json",
            headers=self._headers(),
        )
        res.raise_for_status()
        d = res.json()
        summary = d.get("summary", {})
        sleep = d.get("sleep", [{}])[0] if d.get("sleep") else {}
        return {
            "score": sleep.get("efficiency", "N/A"),
            "total_minutes": summary.get("totalMinutesAsleep", 0),
            "deep_minutes": summary.get("stages", {}).get("deep", 0),
            "rem_minutes": summary.get("stages", {}).get("rem", 0),
            "light_minutes": summary.get("stages", {}).get("light", 0),
            "awake_minutes": summary.get("stages", {}).get("wake", 0),
        }

    def get_steps(self):
        y = self._yesterday()
        s = requests.get(
            f"{self.BASE_URL}/activities/steps/date/{y}/1d.json",
            headers=self._headers(),
        )
        c = requests.get(
            f"{self.BASE_URL}/activities/calories/date/{y}/1d.json",
            headers=self._headers(),
        )
        s.raise_for_status()
        c.raise_for_status()
        return {
            "steps": int(s.json().get("activities-steps", [{}])[0].get("value", 0)),
            "calories": int(
                c.json().get("activities-calories", [{}])[0].get("value", 0)
            ),
        }

    def get_heart_rate(self):
        y = self._yesterday()
        hr = requests.get(
            f"{self.BASE_URL}/activities/heart/date/{y}/1d.json",
            headers=self._headers(),
        )
        hr.raise_for_status()
        rhr = (
            hr.json()
            .get("activities-heart", [{}])[0]
            .get("value", {})
            .get("restingHeartRate", "N/A")
        )
        hrv_res = requests.get(
            f"{self.BASE_URL}/hrv/date/{y}.json", headers=self._headers()
        )
        hrv = "N/A"
        if hrv_res.status_code == 200:
            hrv_data = hrv_res.json().get("hrv", [])
            if hrv_data:
                v = hrv_data[0].get("value", {}).get("dailyRmssd", "N/A")
                hrv = round(v, 1) if isinstance(v, float) else v
        return {"resting_heart_rate": rhr, "hrv": hrv}
