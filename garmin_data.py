import os
from datetime import date, datetime, timedelta

from garminconnect import Garmin

TOKENS = os.path.expanduser("~/.config/garmin-health/tokens")
SERIES_POINTS = 96  # downsample today's HR to ~15 min buckets for the chart

_api = None


def get_api():
    """Reuse one logged-in client so garth can refresh tokens in place."""
    global _api
    if _api is None:
        api = Garmin("", "")
        api.login(tokenstore=TOKENS)
        _api = api
    return _api


def reset_api():
    global _api
    _api = None


def latest_value(values, index=1, minimum=0):
    """Newest (timestamp, value) whose value is a real reading.

    Garmin pads arrays with None and uses negative sentinels (-1 = not
    measured, -2 = activity) for stress, so those are skipped.
    """
    for row in reversed(values or []):
        if not isinstance(row, (list, tuple)) or len(row) <= index:
            continue
        val = row[index]
        if isinstance(val, (int, float)) and val >= minimum:
            return row[0], val
    return None


def downsample(values, points=SERIES_POINTS):
    rows = [
        (r[0], r[1])
        for r in values or []
        if isinstance(r, (list, tuple)) and len(r) > 1 and isinstance(r[1], (int, float)) and r[1] > 0
    ]
    if len(rows) <= points:
        return [[ts, v] for ts, v in rows]
    step = len(rows) / points
    out = []
    for i in range(points):
        chunk = rows[int(i * step):int((i + 1) * step)] or [rows[-1]]
        out.append([chunk[-1][0], round(sum(v for _, v in chunk) / len(chunk))])
    return out


def _heart_rates(api):
    """Today's HR, or yesterday's if the watch hasn't synced anything yet."""
    today = date.today()
    hr = api.get_heart_rates(today.isoformat())
    if latest_value(hr.get("heartRateValues"), minimum=1):
        return today, hr
    yesterday = today - timedelta(days=1)
    prev = api.get_heart_rates(yesterday.isoformat())
    if latest_value(prev.get("heartRateValues"), minimum=1):
        return yesterday, prev
    return today, hr


def fetch_stats():
    try:
        return _fetch(get_api())
    except Exception:
        # Drop the client so the next poll re-reads tokens from disk.
        reset_api()
        raise


def _fetch(api):
    day, hr = _heart_rates(api)
    day_s = day.isoformat()
    hr_values = hr.get("heartRateValues") or []
    latest = latest_value(hr_values, minimum=1)

    body_battery = None
    stress = None
    try:
        stress_data = api.get_all_day_stress(day_s)
        bb = latest_value(stress_data.get("bodyBatteryValuesArray"), index=2)
        st = latest_value(stress_data.get("stressValuesArray"))
        body_battery = bb[1] if bb else None
        stress = st[1] if st else None
    except Exception:
        pass

    steps = None
    step_goal = None
    try:
        steps_data = api.get_daily_steps(day_s, day_s)
        if isinstance(steps_data, list) and steps_data:
            steps = steps_data[0].get("totalSteps")
            step_goal = steps_data[0].get("stepGoal")
    except Exception:
        pass

    hr_ts = latest[0] / 1000 if latest else None
    return {
        "day": day_s,
        "heart_rate": latest[1] if latest else None,
        "hr_ts": hr_ts,
        "fresh_minutes": (
            int((datetime.now().timestamp() - hr_ts) / 60) if hr_ts else None
        ),
        "resting_hr": hr.get("restingHeartRate"),
        "resting_hr_7d": hr.get("lastSevenDaysAvgRestingHeartRate"),
        "hr_min": hr.get("minHeartRate"),
        "hr_max": hr.get("maxHeartRate"),
        "hr_series": downsample(hr_values),
        "body_battery": body_battery,
        "stress": stress,
        "steps": steps,
        "step_goal": step_goal,
    }
