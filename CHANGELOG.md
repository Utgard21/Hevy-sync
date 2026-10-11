# Changelog

This file tracks user-visible changes. The project currently identifies its stable release as **v1.0.0**; the entries below describe updates on the `main` branch and the `latest` container image, not a newly tagged release.

## Unreleased — 2026-10-11

### Added
- Hevy body-measurement import during normal API synchronization, with local history and trend displays.
- Source labels distinguishing imported Hevy measurements from manually entered values.
- Workout-history filtering by routine, exercise, and date; quick date presets.
- Pinned Overview metrics, stored as browser preferences.
- Separate timestamps for last sync attempt and last successful sync.
- Recorded-versus-calculated metric provenance labels and explanatory text.

### Changed
- Imported measurements are read-only in the dashboard; manual measurements take display priority for the same date and metric, while both underlying sources are retained.
- Updated README, Unraid Community Applications template, usage notes, and deployment documentation.

### Compatibility
- No additional environment variables, ports, or mounts are required.
- Existing persistent SQLite data and manual measurements must be retained across updates.

## Earlier functionality

Workout analytics, training calendar, monthly reports, muscle heatmap, PR tracking, workout CSV import, Hevy API synchronization, Docker/Unraid deployment, and optional Basic Authentication were available before these updates.
