# Hevy Progress

**v1.0.0** · Available in Unraid Community Applications · Docker / Unraid · Self-hosted · MIT


A colorful, privacy-focused, self-hosted training analytics dashboard for [Hevy](https://hevy.com/), designed for Docker and Unraid.

> **Now available in Unraid Community Applications.** Open **Apps**, search for **Hevy Progress**, and install it directly.

> **Unofficial project.** Hevy Progress is independent and is not affiliated with, endorsed by, or maintained by Hevy.

> **Built for my own training workflow.** I originally built and configured Hevy Progress around my own needs, workout data, training habits, and self-hosted setup. I am sharing it because it may be useful to others, but your Hevy data and preferences may be different. Some analytics, exercise/muscle mappings, defaults, goals, UI choices, or deployment settings may need to be adjusted for your own use. Please review the results rather than assuming every default is a perfect fit for your training.

## What it does

Hevy Progress turns your workout history into a private dashboard with:

- Overview, Progress, Analytics, Muscles, Calendar, and full-history Reports views
- Workout frequency, volume, sets, reps, duration, streaks, and lifetime totals
- Exercise progression, rep PRs, estimated 1RM, PR timeline, and mini trend cards
- Interactive front/back muscle heatmap, primary/secondary muscle contribution analytics, recovery view, and weekly muscle sets
- Full-history training calendar and separated monthly reports with month-over-month comparisons, highlights, muscle distribution, and workout history
- Automatic Hevy API sync or CSV import
- Persistent SQLite storage and JSON backup
- Optional HTTP Basic Authentication
- Multi-architecture Docker images for `linux/amd64` and `linux/arm64`

## Demo & screenshots

A privacy-safe sample file is included at `demo/demo-workouts.csv`. Import it into a fresh/test instance to populate the dashboard for screenshots or to explore the UI without connecting a Hevy account.

**Do not use demo data in your real instance unless you want those sample workouts stored alongside your own data.**

Screenshots for the public listing should be captured from this demo dataset rather than a personal workout database.

## Unraid Community Applications

**Hevy Progress is available in the Unraid Community Applications catalog.**

1. Open the **Apps** tab in Unraid.
2. Search for **Hevy Progress**.
3. Select the app and install it.
4. Add your Hevy API key if you want automatic API synchronization, or import a Hevy CSV export from the dashboard.

The native Unraid template is also included in this repository as `hevy-progress.xml`.

### Unraid “Last Update” metadata

Hevy Progress runs from GHCR (`ghcr.io/utgard21/hevy-sync:latest`). The current Community Applications client calculates the sidebar **Last Update** value for GHCR images by looking up a same-name repository on Docker Hub. If that Docker Hub mirror does not exist, Unraid can show **Unknown** even though the GHCR image and the Community Applications template are current.

This repository keeps GHCR as the canonical runtime registry. The GitHub Actions workflow also supports an optional Docker Hub metadata mirror. To enable it:

1. Create a public Docker Hub repository named `hevy-sync` under the same Docker Hub username/namespace you want CA to query (for this project, `utgard21/hevy-sync`).
2. Add GitHub Actions repository secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`.
3. Push to `main` or manually run the Docker workflow. It will continue publishing GHCR normally and will additionally publish `<DOCKERHUB_USERNAME>/hevy-sync:latest`.
4. Refresh Community Applications after its metadata cache updates.

The XML `<Date>` field is still maintained for Community Applications metadata/changelog purposes, but it does **not** drive this sidebar value for a `:latest` Docker image.

### Container image

Use the container image:

```
ghcr.io/utgard21/hevy-sync:latest
```

Map `/data` to a persistent appdata directory, expose container port `8080`, and add the environment variables you need below.

The Hevy Public API is currently available to Hevy Pro users, and API keys are obtained from Hevy's developer settings. See the [official Hevy API documentation](https://api.hevyapp.com/docs/).

## Docker Compose

```bash
cp .env.example .env
# Edit .env and add your private values.
docker compose up -d --build
```

The included Compose file publishes the dashboard at port `8085`.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `HEVY_API_KEY` | empty | Optional Hevy API key |
| `DATA_DIR` | `/data` | Persistent database directory |
| `TZ` | `Europe/Sofia` | Workout dates and week boundaries |
| `SYNC_INTERVAL` | `3600` | Seconds between API syncs |
| `DASHBOARD_USERNAME` | empty | Optional HTTP Basic Auth username |
| `DASHBOARD_PASSWORD` | empty | Optional HTTP Basic Auth password |

Set **both** dashboard username and password to enable authentication.

## Security & privacy

The repository is safe to keep public **only if secrets and personal workout data stay outside Git**.

- Never commit `.env`, your Hevy API key, dashboard password, SQLite database, CSV exports, or JSON backups.
- The supplied `.gitignore` excludes common secret/config files and personal Hevy data.
- Store persistent workout data only in the mapped `/data` directory.
- If the dashboard is accessible outside your trusted LAN, put it behind HTTPS. Basic Auth does not encrypt credentials by itself.
- Prefer a reverse proxy or private VPN for remote access rather than exposing port 8080 directly to the Internet.
- If a secret was ever committed, removing it from the latest file is **not enough**: rotate the secret and remove it from Git history.

## Data handling

Hevy Progress stores synced/imported workout data locally in SQLite under `/data`. The dashboard does not need your Hevy account password; API access uses `HEVY_API_KEY`.

Warm-up sets are excluded from working-set, rep, and volume totals. Muscle classification prefers Hevy exercise-template metadata when available and falls back to local mappings when necessary. Primary and secondary muscle contributions are clearly presented as inferred analytics; missing weight, reps, distance, or duration are never fabricated.

## Authentication

Set:

```env
DASHBOARD_USERNAME=your_username
DASHBOARD_PASSWORD=use-a-long-unique-password
```

If both are blank, authentication is disabled. If only one is configured, access is denied rather than silently running partially configured authentication.

## Build & test

```bash
python -m unittest discover -s tests -v
node --check static/app.js
docker build -t hevy-dashboard:local .
```

Local run:

```bash
docker run -d \
  --name hevy-dashboard \
  -p 8085:8080 \
  -v /mnt/user/appdata/hevy-dashboard:/data \
  -e TZ=Europe/Sofia \
  hevy-dashboard:local
```

## Backup

Use the dashboard's **Download data backup** action or back up the persistent `/data` directory. Treat backups as private because they contain workout history.

## Public-repository checklist

Before publishing a fork or sending a pull request:

- Run `git status` and confirm no data/export files are staged.
- Search the diff for API keys, passwords, email addresses, hostnames, and private URLs.
- Use `.env.example` for variable names only; keep real values in `.env`.
- Use redacted/demo data for screenshots and bug reports.
- Rotate any credential that was accidentally pushed.

## Hevy attribution

Workout data is obtained from [Hevy](https://hevy.com/) through its public API or user-exported CSV files. Hevy and its branding belong to their respective owner. This project is an independent analytics dashboard.

## Release

The first stable public release is **v1.0.0**. The container continues to publish `latest`, while version tags provide reproducible release images.

## License

MIT License. See [LICENSE](LICENSE).

## Contributing

Issues and pull requests are welcome. Please do not attach personal workout exports, API keys, passwords, or unredacted database files to public issues.
