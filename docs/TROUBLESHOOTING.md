# FAQ and troubleshooting

## Hevy measurements are not showing

1. Confirm you entered body measurements in the **Hevy app** and have a valid `HEVY_API_KEY` in the Unraid container.
2. Click **Sync Hevy** and check the **last attempt**, **last successful sync**, and any error message. An attempt is not necessarily a successful import.
3. Confirm the API account and permissions support the body-measurement endpoint. Availability and returned fields may vary.
4. Verify the container can reach `api.hevyapp.com` and that its `/data` directory is writable.
5. Check that your measurements use fields supported by the current importer; see [Measurement API notes](MEASUREMENTS-API.md).
6. Do not delete your SQLite database to force a sync. Keep a backup and report a sanitized error if the issue persists.

**Important:** The current synchronization treats body-measurement retrieval as part of the sync operation. An API failure can cause the overall sync to report an error even when cached data remains visible.

## Will automatic sync overwrite manual entries?

No. Hevy-imported and manual measurements live in separate tables. For an identical date and metric, the manual entry is displayed; the imported value remains stored.

## Can I edit a measurement imported from Hevy?

Edit it in Hevy and synchronize again. The dashboard does not offer a local delete action for imported entries. Manually entered values can be managed in the dashboard.

## Why does favorite start time show 16:00?

This is the most frequent **hour bucket** of workout start times in the selected range, not the arithmetic average or an exact start time. The application converts timestamps using its configured `TZ`. If multiple hours tie, the current calculation chooses the earliest matching hour.

## Why do totals differ from Hevy?

Check the selected date range, timezone, warm-up classification, and missing weight/reps. Weighted training volume is calculated from eligible recorded working sets; it is not estimated from missing inputs. Estimated 1RM and muscle allocation are separately labeled.

## Does a Docker update erase workouts?

Not if your `/data` mount stays persistent and unchanged. Always back up the SQLite database before upgrading. See [Unraid upgrade guide](UNRAID-UPGRADE.md).

## Why is Unraid's “Last Update” unknown?

Unraid Community Applications may use Docker Hub metadata even when the app's canonical image is on GHCR. See the README's **Unraid Last Update metadata** section.

## Security

Never post your API key, personal measurements, unredacted workout export, SQLite database, or private network addresses in public issues.
