# Upgrade Hevy My Progress on Unraid

## Before upgrading

1. Open **Docker** in Unraid and note your current Hevy My Progress image, port, and environment settings.
2. Verify that container path `/data` maps to persistent storage (the template default is `/mnt/user/appdata/hevy-progress`).
3. Stop the container briefly and back up the entire appdata directory, including `hevy.sqlite`. Resume only after the copy finishes. Keep backups private.
4. Preserve `HEVY_API_KEY`, `TZ`, `SYNC_INTERVAL`, and any dashboard username/password. No new settings are needed for body-measurement syncing.

## Update

1. In **Docker**, select **Check for Updates** if needed and use **Update** on Hevy My Progress.
2. Keep the same `/data` mapping. **Do not delete the appdata directory** when replacing or recreating the container.
3. Wait for the image pull and container start to finish.
4. Open the dashboard and confirm existing workout history and manual measurements remain present.
5. If using a Hevy API key, select **Sync Hevy** (or wait for the scheduled sync), then check the Measurements tab and sync status.
6. Confirm the health endpoint at `http://UNRAID-IP:YOUR-PORT/health` responds successfully. If authentication is configured, other endpoints may require credentials.

## Troubleshooting and rollback

- If the image does not update, check [GitHub Actions](https://github.com/Utgard21/Hevy-sync/actions) for a successful Docker publish, then refresh the image in Unraid.
- If data is missing, verify that the old and new containers use the **same persistent `/data` host path** before attempting any restore.
- If measurements are missing, see [Troubleshooting](TROUBLESHOOTING.md).
- To roll back, stop the container, deploy a previously known-good image digest or version tag, and restore the matching appdata backup if a schema/data incompatibility occurs. Do not blindly overwrite newer data.
- The repository checkpoint branch is a **source-code rollback point**, not a backup of your local SQLite database.

See the [README](../README.md) for configuration and [Changelog](../CHANGELOG.md) for feature changes.
