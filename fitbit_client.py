import requests
from datetime import date, timedelta

WEEKDAY_LABELS = ["月", "火", "水", "木", "金", "土", "日"]


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

    def _week_range(self):
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=6)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    def get_weekly_sleep(self):
        start, end = self._week_range()
        res = requests.get(
            f"{self.BASE_URL}/sleep/date/{start}/{end}.json",
            headers=self._headers(),
        )
        res.raise_for_status()
        d = res.json()
        daily = []
        for s in d.get("sleep", []):
            if s.get("isMainSleep"):
                dt = s.get("dateOfSleep", "")
                day_of_week = WEEKDAY_LABELS[date.fromisoformat(dt).weekday()] if dt else "?"
                daily.append({
                    "date": dt,
                    "day": day_of_week,
                    "total_minutes": s.get("minutesAsleep", 0),
                    "efficiency": s.get("efficiency", 0),
                })
        total_min = sum(d["total_minutes"] for d in daily)
        avg_min = total_min // len(daily) if daily else 0
        avg_eff = sum(d["efficiency"] for d in daily) // len(daily) if daily else 0
        return {
            "daily": sorted(daily, key=lambda x: x["date"]),
            "avg_minutes": avg_min,
            "avg_efficiency": avg_eff,
        }

    def get_weekly_steps(self):
        start, end = self._week_range()
        s = requests.get(
            f"{self.BASE_URL}/activities/steps/date/{start}/{end}.json",
            headers=self._headers(),
        )
        c = requests.get(
            f"{self.BASE_URL}/activities/calories/date/{start}/{end}.json",
            headers=self._headers(),
        )
        s.raise_for_status()
        c.raise_for_status()
        steps_list = s.json().get("activities-steps", [])
        cal_list = c.json().get("activities-calories", [])
        cal_map = {x["dateTime"]: int(x["value"]) for x in cal_list}
        daily = []
        total_steps = 0
        total_cal = 0
        for entry in steps_list:
            dt = entry["dateTime"]
            st = int(entry["value"])
            cl = cal_map.get(dt, 0)
            day_of_week = WEEKDAY_LABELS[date.fromisoformat(dt).weekday()]
            daily.append({"date": dt, "day": day_of_week, "steps": st, "calories": cl})
            total_steps += st
            total_cal += cl
        n = len(daily) or 1
        return {
            "daily": daily,
            "total_steps": total_steps,
            "avg_steps": total_steps // n,
            "avg_calories": total_cal // n,
        }

    def get_weekly_heart_rate(self):
        start, end = self._week_range()
        hr = requests.get(
            f"{self.BASE_URL}/activities/heart/date/{start}/{end}.json",
            headers=self._headers(),
        )
        hr.raise_for_status()
        rhr_values = []
        for entry in hr.json().get("activities-heart", []):
            r = entry.get("value", {}).get("restingHeartRate")
            if r:
                rhr_values.append(r)
        hrv_res = requests.get(
            f"{self.BASE_URL}/hrv/date/{start}/{end}.json",
            headers=self._headers(),
        )
        hrv_values = []
        if hrv_res.status_code == 200:
            for entry in hrv_res.json().get("hrv", []):
                v = entry.get("value", {}).get("dailyRmssd")
                if isinstance(v, (int, float)):
                    hrv_values.append(v)
        avg_rhr = round(sum(rhr_values) / len(rhr_values), 1) if rhr_values else "N/A"
        avg_hrv = round(sum(hrv_values) / len(hrv_values), 1) if hrv_values else "N/A"
        return {"avg_resting_heart_rate": avg_rhr, "avg_hrv": avg_hrv}
