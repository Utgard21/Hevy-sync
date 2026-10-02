# Hevy Progress for Unraid

A single-container dashboard for visualizing Hevy workout progress on Unraid.

## Docker image

GitHub Actions builds and publishes:

`ghcr.io/utgard21/hevy-sync:latest`

The workflow runs tests first, then builds `linux/amd64` and `linux/arm64` images.

## Main features

- Workouts this week/month and all-time
- Exercise, set, rep, duration and volume statistics
- Weekly activity and training-volume charts
- Activity calendar
- Exercise progression and estimated 1RM
- Recent workouts
- Hourly Hevy API sync
- CSV import
- Persistent SQLite storage
- JSON backup
- Unraid template

## Unraid

Use image:

`ghcr.io/utgard21/hevy-sync:latest`

Map `/data` to a persistent appdata directory and expose container port `8080`.

Set `HEVY_API_KEY` to your Hevy API key, or leave it blank and import Hevy CSV exports.

Default timezone is `Europe/Sofia`.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| HEVY_API_KEY | empty | Optional Hevy API key |
| DATA_DIR | /data | Persistent database directory |
| TZ | Europe/Sofia | Workout dates and week boundaries |
| SYNC_INTERVAL | 3600 | Seconds between API syncs |
| DASHBOARD_USERNAME | empty | Optional HTTP Basic Auth username |
| DASHBOARD_PASSWORD | empty | Optional HTTP Basic Auth password |

Set both `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` to protect the dashboard and API. If both are blank, authentication is disabled. Use HTTPS through your reverse proxy if the dashboard is reachable outside your trusted LAN, because Basic Auth credentials are only protected in transit by HTTPS.

## Local test

```bash
python -m unittest discover -s tests -v
node --check static/app.js
```

## Local Docker build

```bash
docker build -t hevy-dashboard:local .
docker run -d --name hevy-dashboard -p 8085:8080 -v /mnt/user/appdata/hevy-dashboard:/data -e TZ=Europe/Sofia hevy-dashboard:local
```

This is an independent project and is not affiliated with Hevy.

## Dashboard tools

Weekly goals and the default preset range now save in SQLite on the server and are shared across devices using this dashboard. They are shared settings, not separate user profiles. Old browser-only targets are not automatically migrated. Custom date ranges are inclusive and compare against the immediately preceding period of equal length. Custom ranges are not saved as the default.

Charts expose exact values on hover, keyboard focus, or tap. Data checks report exact duplicate records (already excluded from statistics), empty workouts, future timestamps, and durations outside 0–240 minutes. These are review flags, not automatic fixes. Same-weight progression compares best working-set reps at an identical logged weight, first versus latest session within the chosen range.
