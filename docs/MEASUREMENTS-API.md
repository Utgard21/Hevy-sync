# Body measurements: API and data mapping

## Source

Hevy My Progress fetches paginated body-measurement records from the Hevy Public API using the existing `HEVY_API_KEY` during its normal sync. The current importer requests `/v1/body_measurements` and expects a `body_measurements` collection with a `date` field in `YYYY-MM-DD` format. The exact fields exposed by Hevy may depend on the account and API response; this document describes **what the current code recognizes**, not a guarantee that Hevy returns every field.

## Current importer mapping

| API field | Stored metric | Unit |
|---|---|---|
| `weight_kg` | `weight` | kg |
| `lean_mass_kg` | `lean_mass` | kg |
| `fat_percent` | `body_fat` | % |
| `waist` | `waist` | cm (expected) |
| `chest_cm` | `chest` | cm |
| `hips` | `hips` | cm (expected) |
| `neck_cm` | `neck` | cm |
| `shoulder_cm` | `shoulders` | cm |
| `abdomen` | `abdomen` | cm (expected) |
| `left_bicep_cm`, `right_bicep_cm` | `left_biceps`, `right_biceps` | cm |
| `left_thigh`, `right_thigh` | `left_thigh`, `right_thigh` | cm (expected) |
| `left_calf`, `right_calf` | `left_calf`, `right_calf` | cm (expected) |
| `left_forearm_cm`, `right_forearm_cm` | `left_forearm`, `right_forearm` | cm |

**Schema caution:** Names without unit suffixes and account-specific API availability have not been validated against your live Hevy response. Check the [official Hevy API docs](https://api.hevyapp.com/docs/) and a sanitized response before assuming those fields are present or measured in centimeters. Unsupported fields are ignored rather than invented.

## Storage and precedence

- Hevy-imported measurements: `hevy_measurements(day, metric, value)`.
- Manual measurements: `measurements(day, metric, value)`.
- Both tables reside in the persistent SQLite database under `/data`.
- The API response at `GET /api/measurements` merges both tables, adding a `source` value of `Hevy` or `Manual`. Manual values take display precedence for the same date and metric.
- Imported values are read-only in the dashboard; editing a Hevy value requires changing it in Hevy and syncing again.
- Sync replaces the imported snapshot only after retrieval and validation; manual records are not deleted.

No body values are calculated from workouts. If a field is absent, the dashboard must not display an invented value.

## Privacy

Measurements are sensitive personal information. Keep `/data`, database backups, and API keys private, and secure remote dashboard access with HTTPS and authentication.
