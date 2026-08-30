import os
from datetime import datetime

from garminconnect import Garmin

TOKENS = os.path.expanduser("~/.config/garmin-health/tokens")


def latest_value(values, index=1):
    if not values:
        return None
    for row in reversed(values):
        if not isinstance(row, (list, tuple)) or len(row) <= index:
            continue
        val = row[index]
        if val:
            return row[0], val
    return None


def fetch_stats():
    api = Garmin("", "")
    api.login(tokenstore=TOKENS)

    today = datetime.now().strftime("%Y-%m-%d")

    hr = api.get_heart_rates(today)
    latest = latest_value(hr.get("heartRateValues") or [])
    fresh_ts = latest[0] / 1000 if latest else None
    fresh_minutes = (
        int((datetime.now().timestamp() - fresh_ts) / 60) if fresh_ts else None
    )

    body_battery = None
    stress = None
    try:
        stress_data = api.get_all_day_stress(today)
        bb = latest_value(stress_data.get("bodyBatteryValuesArray") or [], index=2)
        st = latest_value(stress_data.get("stressValuesArray") or [])
        body_battery = bb[1] if bb else None
        stress = st[1] if st else None
    except Exception:
        pass

    steps = None
    step_goal = None
    try:
        steps_data = api.get_daily_steps(today, today)
        if isinstance(steps_data, list) and steps_data:
            steps = steps_data[0].get("totalSteps")
            step_goal = steps_data[0].get("stepGoal")
    except Exception:
        pass

    return {
        "heart_rate": latest[1] if latest else None,
        "resting_hr": hr.get("restingHeartRate"),
        "body_battery": body_battery,
        "stress": stress,
        "steps": steps,
        "step_goal": step_goal,
        "fresh_minutes": fresh_minutes,
    }