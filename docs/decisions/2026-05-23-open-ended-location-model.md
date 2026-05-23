# Open-Ended Configured Location Model

Date: 2026-05-23

## Status

Accepted

## Decision

The integration should move from a fixed office-and-remote config model to an open-ended configured-location list.

The first durable shape is:

- `configured_locations`

Each configured location record stores:

- `site_id`
- `label`
- `enabled`
- `site_type`
- `coordinate_behavior`
- `distance`

`site_id` remains the stable backend identity.

`label` is user-overridable presentation only.

`site_type` remains a compatibility routing semantic for now and is inferred from backend data in the first implementation slice.

`coordinate_behavior` is the primary runtime routing semantic for how action coordinates are produced per configured location.

Current supported values are:

- `device_tracker`
- `remote_zero`

No third coordinate-behavior mode is currently in scope. A new mode should only be added when a concrete Sign In App scenario requires a distinct runtime rule.

`distance` carries the location-specific accuracy parameter for `device_tracker` routing behavior.

## Action surface

Service actions should prefer a concrete `site_id` input.

Compatibility `site_type` inputs remain supported during migration:

- `office`
- `remote`

`site_id` is the preferred action input.

`site_type` remains a backward-compatible routing hint.

Compatibility hints remain supported rather than scheduled for immediate deprecation, but they are explicitly non-primary and should not gain richer semantics than the concrete `site_id` surface.

When a compatibility hint matches more than one configured location, the action must not pick one by list order.

Hint-based actions should:

- resolve uniquely when exactly one configured location matches
- allow sign-out to use current active-session context when that disambiguates a matching configured location
- otherwise fail as routing ambiguity and require a concrete `site_id`

## Config-flow shape

After companion-code entry, config flow should iterate across all backend-discovered sites in one step.

For each site it should allow:

- inclusion or exclusion
- a suggested backend-derived label
- label override
- distance input for `device_tracker` sites

Configured sites missing from later backend rediscovery should still be preserved during reconfiguration rather than silently dropped.

## Consequences

The integration must keep supporting legacy entries that only store:

- `office_site_id`
- `remote_site_id`
- `office_distance`

Migration therefore proceeds by:

1. adding `configured_locations`
2. teaching runtime logic and services to read both models
3. moving config flow to write the new model
4. making runtime coordinate resolution prefer configured-location behavior over compatibility hints
5. keeping compatibility hints until the concrete-site action surface is established
