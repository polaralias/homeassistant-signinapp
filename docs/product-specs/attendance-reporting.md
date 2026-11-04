---
type: "Product Contract"
title: "Attendance reporting and quotas"
description: "API-backed attendance, activities and opt-in holiday-aware quota conversion."
timestamp: 2026-11-04T18:00:00Z
authority: canonical
verification: tested
owner: polaralias
tags: [signinapp, reporting, quotas]
---
# Attendance reporting and quotas

The integration reads the companion account's own `/api/mobile/history` records using its existing credential. It derives exact durations from backend timestamps, independently of HA recorder retention and sampling. No reporting action changes attendance. The existing primary status entity, service routes, identity and credential recovery remain stable.

See the [dated history contract](../references/observed-history-contract-2026-11-04.md)
for observed wire behavior and its limits. Existing [attendance automation](attendance-automation.md)
routing and mutation guarantees continue to apply.

Reporting periods are today, this week (Monday-based), this calendar month, current configured quota period, yesterday, week through yesterday, and each day of this week. Each period exposes signed-in, working, non-working, unclassified working/activity time, session count, each backend activity type, quota target, used, remaining, overtime, signed balance, completed/remaining/overtime percentages, nominal quota and holiday reduction. Each activity also offers its percentage of signed-in time, working time (where applicable), and quota contribution. Activity and entity identity use stable backend activity IDs; label edits do not create duplicate entities. Secondary daily quota/activity combinations and activity percentages are offered disabled by default to avoid flooding dashboards. Quota entities outside the base period are unavailable while rollups are disabled.

Recorded time stays exact in hours. Rounding to quarter hours belongs to notification/dashboard presentation, never calculation. Sessions are clipped at local calendar boundaries; UTC elapsed seconds preserve DST correctness. Duplicates cannot inflate time, overlapping sessions use interval unions, malformed records do not become fabricated zeros, and uncertain working classification makes working-based quota progress unavailable while signed-in time stays usable.

The quota input is an amount of hours for N days, N weeks or N calendar months, anchored to an explicit date. Default is 37.5 hours per one Monday-based week. Bounds are one year (366 days, 52 weeks or 12 months) to keep remote history requests bounded. This supports ten-day, fortnightly, quarterly, six-month and annual contracts. Quota progress uses working activities by default; signed-in basis is separately configurable. Progress may exceed 100%; remaining time clamps at zero and overtime is reported separately.

Quota rollups and public-holiday adjustment are independent opt-ins, off by default. Without rollups, quota metrics apply to the configured base period and any matching calendar period. With rollups, the base quota is distributed across its ordinary selected workdays, then summed into reporting periods. For a monthly base quota, each month's ordinary workday count determines that month's allocation. Holiday adjustment removes allocations on the selected region's public holidays or explicit custom dates; it does not increase other workdays' hours. Nominal and adjusted quota remain visible separately. Holiday dates are calculated locally using the same maintained `holidays` library used by HA Workday; no runtime holiday API credential or web service is required. Holiday observance follows the selected country/subdivision. Custom dates are explicit ISO dates, and bank-holiday changes require a library update.

History is shared by all entities, fetched in at most 45-day chunks, refreshed every five minutes and after attendance changes; active durations project from a verified snapshot every minute. A history permission failure must not take down current attendance. Authentication failures initiate existing reauthentication. New activity types discovered after setup create additional stable activity entities. Options changes reload the entry and preserve existing sensor identities.

## Acceptance and verification

| Behaviour | Required checks |
|---|---|
| Actual recorded duration | Multiple sessions; corrections; duplicate IDs; overlaps; invalid timestamps; own-account list response |
| Period boundaries | Midnight, Monday reset, month/year change, leap day, spring/autumn DST, live and omitted open sessions |
| Activities | Working/break transitions, archived types, renamed/new types, missing and contradictory classification |
| Quotas | Default weekly; rollups off/on; ten days, fortnight, monthly, six months; zero quota; overtime; custom workdays |
| Holidays | Country/subdivision, observed holidays, explicit dates, off by default, nominal versus adjusted target |
| HA lifecycle | Primary status preserved; history errors isolated; retries/read caching; dynamic discovery; options reload; unique IDs |
| Live migration | Backend totals checked, prior UI/notification IDs mapped without `_2`, private visibility retained, no attendance test mutations |

The implemented 1.1.0 reliability branch is a dependency until its separate PR is merged. This feature must not revert those deployed fixes when released.

Verification on 4 November 2026: 127 tests passed with HA 2025.1.4. The full
126-test suite run with HA 2026.10.4 passed, and the latest 37 focused
reporting/transport/options tests (including activity percentages) also passed
with that version. A live HA 2026.10.4
installation loaded the integration and all report identities; country and region
options forms were exercised without saving alternative settings. Independent
calculations agreed with the account's closed-session history, including an
overnight interval and non-working time. Eleven former History Stats entity IDs
were assigned to the corresponding native reports; primary identity, dashboard
configuration and notification configurations remained unchanged. No attendance
mutation or test notification was sent. Active-session wire shape remains a
defensive synthetic-test contract pending a suitable read-only observation.
