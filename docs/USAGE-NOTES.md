# Hevy Progress — Usage Notes

Hevy Progress started as a personal project built around the maintainer's own training workflow, Hevy data, preferences, and Unraid/Docker environment. It is published as an open-source project because it may also be useful to other Hevy users, but it is not intended to imply that one configuration or interpretation fits everyone.

## Before relying on the dashboard

Your exercise library, naming, workout structure, goals, available Hevy metadata, and training style may differ from the maintainer's. Review the dashboard after importing or syncing your data and adjust the project where appropriate.

Areas that may reasonably need customization include:

- exercise and fallback muscle mappings;
- training goals and the way you interpret streaks;
- timezone, sync interval, ports, authentication, and persistent-data paths;
- which analytics and report sections are useful to you;
- UI labels, layout, and presentation preferences.

## Data and analytics

Hevy Progress tries to preserve a clear distinction between recorded and derived information. Recorded values come from Hevy/API or CSV data. Exact totals are calculated from those recorded values. Estimated or inferred analytics, such as estimated 1RM and muscle attribution, should be interpreted as analytical aids rather than additional recorded Hevy data.

Missing weight, repetitions, distance, or duration should not be invented merely to complete a statistic. Exercise-template metadata from Hevy is preferred for muscle classification when available, with local mappings used as a fallback.

Because exercise libraries and training styles vary, inspect fallback mappings if a muscle chart looks wrong for your exercises. A mapping that makes sense for the maintainer's program may not accurately represent a differently named or performed exercise.

## Contributions and forks

If your needs differ, feel free to fork the project and change its defaults or analytics. General improvements that preserve data integrity and are useful beyond one person's training setup are welcome as pull requests.

When reporting problems, use demo or redacted data. Do not publish Hevy API keys, passwords, private workout exports, SQLite databases, or unredacted backups.
