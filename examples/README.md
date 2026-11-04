---
type: "Configuration Guide"
title: "Attendance automation and dashboard examples"
description: "Generic zone, polygon, notification and reporting dashboard configurations."
timestamp: 2026-11-04T20:00:00Z
authority: canonical
verification: tested
owner: polaralias
tags: [examples, automation, dashboard, reporting]
---
# Attendance automation and dashboard examples

These configurations demonstrate the integration's services and native reporting
entities with fictional site IDs and generic entity aliases. They contain no
account credentials or exported account configuration. Replace the aliases and
marked placeholders with entities from your installation before enabling them.

Read the [reporting contract](../docs/product-specs/attendance-reporting.md) for
duration, activity, quota and holiday semantics, and the
[attendance contract](../docs/product-specs/attendance-automation.md) for routing.

## Files

| File | Purpose |
|---|---|
| [packages/attendance.yaml](packages/attendance.yaml) | Shared helpers, confirmed-state notifications, cumulative daily reminder, daily/weekly recap and notification cleanup |
| [packages/presence-zone.yaml](packages/presence-zone.yaml) | Native circular HA zone arrival/departure, stability checks and restart recovery |
| [packages/presence-custom-zone.yaml](packages/presence-custom-zone.yaml) | Alternative polygon arrival/departure using trusted membership for one tracked person |
| [dashboard/attendance.yaml](dashboard/attendance.yaml) | Manual buttons, status/presence, horizontal weekly/day strip and expandable reports |
| [dashboard/entity-aliases.yaml](dashboard/entity-aliases.yaml) | Generic reporting aliases mapped to `report_period`, `report_metric` and activity labels |

Use **one** presence package. The circular and polygon files intentionally share
automation IDs and the same visit latch; they are alternatives, not two attendance
controllers to run together. The shared package and dashboard work with either.

## Map the entities and sites

1. Configure Sign In App and include the locations you want to use.
2. Find the integration device in **Settings → Devices & services**. Replace
   `REPLACE_WITH_DEVICE_ID` with that device ID. This selects the account when
   several entries exist; it is not an API token.
3. Replace fictional site `1001` with a configured primary site ID and `2002` with
   a configured secondary site ID. Site IDs select locations, not HA zone IDs.
   The status sensor exposes `active_work_location_id` and
   `last_active_work_location_id` for identifying current and recent locations.
4. Replace `person.attendee`, `zone.campus`, `sensor.customzone_campus`,
   `sensor.attendee_status` and the two `notify.mobile_app_*_phone` actions with
   the corresponding entities/actions on your system.
   For the native-zone alternative, point the dashboard's Presence tile at
   `person.attendee`; the polygon example uses `sensor.customzone_campus` there.
5. For reporting entities, use the alias guide to identify the native sensor by
   its attributes. Replace the example alias throughout, or rename that entity
   in HA's entity settings. Entity names depend on the configured account label;
   the aliases shown here are a convention for these examples, not guaranteed
   automatically generated entity IDs.
6. Enable disabled reporting entities referenced by the dashboard, including
   activity percentages. Enable quota rollups if displaying daily/monthly quotas
   from a weekly contract. A percentage of working time applies only to working
   activity types; the example does not request it for breaks or other non-working
   activities.

The alias guide describes entity matching. It is not a `configuration.yaml` file.
Activity labels in it are illustrative; match your own backend activity IDs/labels.
Entity registry edits preserve native calculation; no History Stats helper or
template counter is required. Keep `report_period` and `report_metric` matching
the guide even when choosing different entity IDs.

## Load the automation packages

Enable packages in the existing `homeassistant` section of `configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Copy `packages/attendance.yaml` and the chosen presence file into that directory
after making the replacements. Validate configuration, then load the changed
helpers and automations through your usual HA configuration workflow. Merge into
an existing packages configuration rather than adding a second `homeassistant`
key. The presence automation aliases are `Attendance arrival` and `Attendance
departure`; if HA assigns different automation entity IDs, update their self-enable
triggers too.

### Native circular zone

The circular example uses HA's `zone` enter/leave triggers for `person.attendee`
and `zone.campus`. It waits one minute on arrival and two on departure, cancelling
if the reading becomes uncertain or changes direction. It also checks coordinates,
a known person state and a location update within five minutes. Zone names come
from the zone's `friendly_name`, rather than a hardcoded person state label.

On startup, automation reload or re-enable, it reconciles the current location
after a fresh full stability wait. Unavailable location data cannot satisfy the
departure condition. Native circular zones do not provide polygon distance or
per-tracker confidence classifications; use the next alternative for those.

### Custom polygon zone

Install [Custom Zone](https://github.com/polaralias/homeassistant-customzones), draw
the polygon and select the person/tracker to monitor. Substitute the created sensor
for `sensor.customzone_campus`. The automation checks whether `person.attendee`
appears in `trackers_in_zone` or `trackers_out_of_zone`, not the aggregate count or
the old `In zone` text.

An unusable or stale tracker appears in neither trusted list and therefore cannot
cause departure. Another tracked person entering the same polygon does not sign
this attendee in. The same one/two-minute stability, weekday, visit-latch and
startup/reload recovery rules apply.

### Arrival, departure and optional side effects

On confirmed weekday arrival, the controller disables the critical-alert helper,
sets the persistent visit latch, optionally notifies a contact, refreshes attendance
and signs in only from confirmed `signed_out`. On confirmed departure with an active
visit, it enables the alert helper, releases the latch, refreshes attendance and
signs out only if the currently active site matches the configured primary site.
It does not sign out a different location or turn `unknown` into a command.

`input_boolean.attendance_critical_alerts` is an example policy switch. Other alarm
automations must consult it; toggling it alone does not change phone permissions or
silence a handset. The contact notification action is optional and uses
`continue_on_error` so a missing contact notifier does not stop attendance handling.
The latch prevents repeated arrival side effects after GPS confidence drops and
recovers. Attendance mutations are never automatically retried: an unconfirmed
command may already have reached the backend.

The weekday restriction is deliberate. For a different working pattern, change
all weekday checks consistently, including the repeated checks after stability waits.

## Notifications and totals

The shared package includes:

- A primary-site sign-in notification after a confirmed sign-in or site change.
- A confirmed sign-out notification with cumulative day and week totals across
  all sites. It refreshes native reports and selects completed-period sensors if
  the event crosses midnight; it never extrapolates a recorder counter.
- A once-per-day reminder at **eight cumulative signed-in hours**. This is an
  illustrative threshold: change both the comparison and message to suit your
  policy. A restored date marker prevents duplicates after restart/reload.
- A midnight recap of the completed day and that day's Monday-based week, with
  startup/reload and five-minute catch-up. Saturday's midnight recap uses the
  completed Friday's weekly total. Monday's recap does not accidentally read the
  newly reset current-week sensor. Open sessions flow into the new day in the
  integration's reporting calculations.
- Event-based clearing of sign-in/reminder notifications at sign-out, reminder
  clearing at midnight, Android notification timeouts and a scheduled tag cleanup.

Durations displayed in messages and the horizontal strip round to the nearest
15 minutes, with halfway values rounded up. Sensors, reminder thresholds and quota
calculations remain exact. Signed-in totals include non-working activities;
working-based quota progress excludes them. If a report is unavailable, the
notification does not pretend its total is zero.

The notification format uses title `Sign in update 🔐`, a briefcase icon, stable
tags, group/channel `Sign In Updates`, and a click route to `/lovelace/attendance`.
The optional contact arrival message uses a location-update title. Change the
route when using a different dashboard URL. The example's six-hour Android timeout
and 06:00 tag cleanup are configurable; clearing is always scoped to listed tags,
not every notification on a phone. The contact arrival tag can be added to that
contact's own clearing policy.

## Dashboard

Create an Attendance view from `dashboard/attendance.yaml`, or merge its two
sections into an existing Sections dashboard. Replace `REPLACE_WITH_HA_USER_ID`
with the user selected for the private view. Both sections use the same visibility
condition. The first section includes primary/secondary site buttons, sign-out,
status, presence and a horizontal weekly/day strip. Its seven day cells explicitly
read their own entities, including when nested under the weekly parent card.

The second section is one native **entities card**. It uses
[fold-entity-row](https://github.com/thomasloven/lovelace-fold-entity-row) inside the
card: each period expands into totals, quota details, activities and reporting
quality. Activity rows contain a further fold for percentages. This week starts
expanded; other groups can be opened as needed. All rows use actual integration
entities rather than calculations in dashboard templates.

Install these frontend cards through HACS:

- [Button Card](https://github.com/custom-cards/button-card) for the horizontal strip.
- [fold-entity-row](https://github.com/thomasloven/lovelace-fold-entity-row) for nested report rows.

The resource paths normally used by HACS are:

```yaml
resources:
  - url: /hacsfiles/button-card/button-card.js
    type: module
  - url: /hacsfiles/lovelace-fold-entity-row/fold-entity-row.js
    type: module
```

Manage resources through the dashboard resources settings when using storage mode.
Keep the section's visibility condition when moving cards. The view uses the
existing theme's accent/text colours and native entity formatting.

For a weekly contract, enable daily/monthly rollups in the integration's Configure
options to populate those quota rows. For example, **40 hours per one week**, five
weekdays, optional country/subdivision holidays and optional custom ISO dates.
Other base periods use the same UI: one day, two weeks, ten days, three months,
six months or twelve months. Holiday adjustments and rollups are independent
opt-ins; public defaults do not require either.

## Verification boundary

Examples are checked with synthetic data for YAML/HA automation schema validity,
template compilation, trusted versus unusable membership, quarter-hour rounding,
entity-reference consistency and nested day-cell independence. The underlying
integration and corresponding dashboard pattern have runtime evidence; these
generic files still require installation-specific IDs and phone actions before use.
Validation does not send a notification or perform an attendance mutation.
