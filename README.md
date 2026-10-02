# garmin-stats

Cyberpunk bio-monitor for [Omarchy](https://omarchy.org/): live Garmin Connect stats in the bar, plus a local HUD webapp (heart + ECG sweep).

Reads from Garmin Connect (unofficial API) — not live BLE. Data freshness follows your phone↔watch sync.

## What you get

- **Bar widget** — heartbeat icon + BPM, tooltip with resting HR, body battery, stress, steps
- **Dashboard** — `http://localhost:8765` — Cpunk-themed HUD with pulsing heart, draw-then-blank ECG through the heart, scrolling rhythm strip
- **Click the bar** — opens/focuses the dashboard as an Omarchy webapp

## Requirements

- Python 3.11+
- Garmin Connect account
- Linux + BlueZ not required (cloud API only)

## Setup

```bash
python3 -m venv ~/.venvs/garmin
~/.venvs/garmin/bin/pip install -r requirements.txt

mkdir -p ~/.config/garmin-health
cp garmin_data.py server.py ~/.config/garmin-health/
cp -r webapp ~/.config/garmin-health/

# login scripts on PATH
install -m 755 garmin-login garmin-health ~/.local/bin/
# point shebangs at the venv, or:
#   ln -sf ~/.venvs/garmin/bin/python ~/.local/bin/python-garmin
```

Authenticate (tokens go to `~/.config/garmin-health/tokens`, never commit that file):

```bash
garmin-login
garmin-health   # should print Waybar JSON
```

Run the HUD server:

```bash
# one-shot
~/.venvs/garmin/bin/python ~/.config/garmin-health/server.py

# or systemd --user
mkdir -p ~/.config/systemd/user
sed "s|%h|$HOME|g" garmin-stats.service > ~/.config/systemd/user/garmin-stats.service
# edit ExecStart if your paths differ
systemctl --user daemon-reload
systemctl --user enable --now garmin-stats
```

## Omarchy bar

Add to `~/.config/omarchy/shell.json` in `bar.layout.right`:

```json
{
  "id": "garmin-health",
  "type": "command",
  "exec": "/home/YOU/.local/bin/garmin-health",
  "interval": 300,
  "tooltip": "Garmin health",
  "keepSpace": false,
  "onClick": "omarchy launch or focus webapp garmin-stats http://localhost:8765"
}
```

Optional launcher:

```bash
omarchy webapp install garmin-stats http://localhost:8765 webapp/heart.png
```

## Notes

- Garmin Connect unofficial API is rate-limited; 5-minute polling is safe
- First login may hit 429 on mobile endpoints; MFA still works
- Tokens are Garmin session credentials — keep `tokens` out of git
- `garmin-health` reads the running server's `/api/health` first, so the bar and HUD share one Garmin poll; it only logs in to Garmin itself if the server is down (needs `garmin_data.py` in `~/.config/garmin-health/`)
- Stress readings of -1/-2 (Garmin's "not measured"/"activity" sentinels) are ignored
- Shortly after midnight, before the watch has synced, the HUD shows yesterday's data
- Env overrides for `server.py`: `GARMIN_STATS_PORT` (default 8765), `GARMIN_STATS_INTERVAL` seconds (default 300); `garmin-health` honours `GARMIN_STATS_PORT` / `GARMIN_STATS_URL`
