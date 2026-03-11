import requests
from datetime import date, timedelta
from config import (
    FITBIT_AUTH_URL,
    FITBIT_API_BASE_URL,
    FITBIT_SLEEP_API_BASE_URL,
    WEEKDAY_LABELS,
)


class FitbitClient:
    BASE_URL = FITBIT_API_BASE_URL
    AUTH_URL = FITBIT_AUTH_URL

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

    def _today(self):
        return date.today().strftime("%Y-%m-%d")

    def _yesterday(self):
        return (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    def get_sleep(self):
        """当日の睡眠データを取得（朝に実行し、昨夜〜今朝の睡眠を取得）"""
        res = requests.get(
            f"{FITBIT_SLEEP_API_BASE_URL}/sleep/date/{self._today()}.json",
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
        """当日のアクティビティを取得（夜に実行し、その日の歩数を取得）"""
        y = self._today()
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
        """当日の心拍データを取得（夜に実行し、その日の心拍を取得）"""
        y = self._today()
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

    def _month_range(self):
        """今月: 1日〜昨日"""
        end = date.today() - timedelta(days=1)
        start = end.replace(day=1)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    def _last_month_range(self):
        """先月: 先月1日〜先月末日"""
        today = date.today()
        last_day = today.replace(day=1) - timedelta(days=1)
        first_day = last_day.replace(day=1)
        return first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")

    def get_weekly_sleep(self):
        start, end = self._week_range()
        res = requests.get(
            f"{FITBIT_SLEEP_API_BASE_URL}/sleep/date/{start}/{end}.json",
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

    def _calc_sleep_avg(self, start, end):
        res = requests.get(
            f"{FITBIT_SLEEP_API_BASE_URL}/sleep/date/{start}/{end}.json",
            headers=self._headers(),
        )
        res.raise_for_status()
        daily = [
            s for s in res.json().get("sleep", []) if s.get("isMainSleep")
        ]
        if not daily:
            return 0, 0
        avg_min = sum(s.get("minutesAsleep", 0) for s in daily) // len(daily)
        avg_eff = sum(s.get("efficiency", 0) for s in daily) // len(daily)
        return avg_min, avg_eff

    def get_monthly_sleep(self):
        start, end = self._month_range()
        avg_min, avg_eff = self._calc_sleep_avg(start, end)
        last_start, last_end = self._last_month_range()
        last_avg_min, last_avg_eff = self._calc_sleep_avg(last_start, last_end)
        return {
            "avg_minutes": avg_min,
            "avg_efficiency": avg_eff,
            "last_avg_minutes": last_avg_min,
            "last_avg_efficiency": last_avg_eff,
        }

    def get_monthly_steps(self):
        start, end = self._month_range()
        last_start, last_end = self._last_month_range()

        def _fetch(s, e):
            st = requests.get(
                f"{self.BASE_URL}/activities/steps/date/{s}/{e}.json",
                headers=self._headers(),
            )
            ca = requests.get(
                f"{self.BASE_URL}/activities/calories/date/{s}/{e}.json",
                headers=self._headers(),
            )
            st.raise_for_status()
            ca.raise_for_status()
            steps_list = [int(x["value"]) for x in st.json().get("activities-steps", [])]
            cal_list = [int(x["value"]) for x in ca.json().get("activities-calories", [])]
            n = len(steps_list) or 1
            total_st = sum(steps_list)
            total_ca = sum(cal_list)
            return total_st, total_st // n, total_ca // n

        total, avg, avg_cal = _fetch(start, end)
        last_total, last_avg, last_avg_cal = _fetch(last_start, last_end)
        return {
            "total_steps": total,
            "avg_steps": avg,
            "avg_calories": avg_cal,
            "last_total_steps": last_total,
            "last_avg_steps": last_avg,
            "last_avg_calories": last_avg_cal,
        }

    def get_monthly_heart_rate(self):
        start, end = self._month_range()
        last_start, last_end = self._last_month_range()

        def _fetch(s, e):
            hr = requests.get(
                f"{self.BASE_URL}/activities/heart/date/{s}/{e}.json",
                headers=self._headers(),
            )
            hr.raise_for_status()
            rhr_values = [
                entry.get("value", {}).get("restingHeartRate")
                for entry in hr.json().get("activities-heart", [])
                if entry.get("value", {}).get("restingHeartRate")
            ]
            hrv_res = requests.get(
                f"{self.BASE_URL}/hrv/date/{s}/{e}.json",
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
            return avg_rhr, avg_hrv

        avg_rhr, avg_hrv = _fetch(start, end)
        last_avg_rhr, last_avg_hrv = _fetch(last_start, last_end)
        return {
            "avg_resting_heart_rate": avg_rhr,
            "avg_hrv": avg_hrv,
            "last_avg_resting_heart_rate": last_avg_rhr,
            "last_avg_hrv": last_avg_hrv,
        }
