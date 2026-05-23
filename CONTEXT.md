# Context

## Terms

### Sign In App attendance automation integration

A Home Assistant integration whose purpose is to provide reliable Sign In App attendance automation and state visibility, including first-class setup, per-user configuration, and sign-in or sign-out actions across the user's supported work locations.

### Work location

A product-level location the user can attend through this integration.

### Attendance routing

How the integration resolves the target work location for a user action.

Attendance routing supports distinct sign-in and sign-out verbs. It is not a generic attendance-target setter.

Attendance routing is asymmetric:

- sign-in should prefer explicit user intent and be straightforward
- sign-out may need inference and fallback to recover the active work location safely

Allowed inputs, in precedence order:

1. explicit action input
2. live backend state
3. cached local session state
4. configured user mappings
5. current Home Assistant location context when needed for location semantics

When live backend state and cached local session state disagree, explicit live backend state wins and cached local session state is fallback only.

Explicit action input may be either:

- a concrete work-location identity
- an attendance-routing hint

Routing hints are a compatibility surface, not the desired long-term final model.

The supported transition routing inputs are:

- concrete work-location identity
- office-like routing hint
- remote-like routing hint

Concrete work-location identity is the preferred long-term product input.

Routing hints remain supported for compatibility, but they are a non-primary surface and should not grow new semantics ahead of concrete work-location identity.

If a concrete target is selected and is temporarily unusable, the action should fail rather than silently fall back to a different configured target.

Fallback across configured targets is only appropriate for hint-level actions and only when explicitly allowed by routing policy.

Routing semantics may be discovered from backend hints during config flow and then confirmed in configuration.

They are not intended to be reconfigured during each sign-in or sign-out action.

Routing semantics are the durable configured facts that determine how a work location should behave during attendance routing.

The minimum durable routing semantics for a configured work location are:

- stable backend identity
- user-facing label
- inclusion or enabled state
- coordinate-behavior semantics
- any location-specific parameter required by those semantics

The currently supported coordinate-behavior set is intentionally small:

- `device_tracker`
- `remote_zero`

No third coordinate-behavior mode is currently in scope until a concrete real-world Sign In App scenario requires one.

### Work-location label

The user-facing name for a configured work location.

It may be seeded from backend-discovered names and then overridden by the user during configuration.

Work-location labels are UX only and must not be used as routing identity.

Presentation grouping should be derived from configured routing metadata unless a later concrete need requires durable grouping configuration.

### Work-location identity

The stable backend-derived identity for a configured work location.

Attendance routing and entity identity should use stable backend identity rather than mutable user labels.

Backend state is explicit enough to override cache when it identifies a work location by stable backend identity in a verified authoritative field.

### Primary user attendance entity

The single Home Assistant entity representing the user's overall Sign In App attendance state.

This is the primary state surface for the integration.

Its core state machine should use canonical status classes.

Work-location identity and label should be structured metadata or presentation, not the fundamental state vocabulary.

When present, active and last-active work-location identity and label belong in structured attributes rather than the core state field.

Last-active work-location context is part of the operational contract, not only UX presentation.

The primary entity should expose a stable attribute model including:

- `status_class`
- `active_work_location_id`
- `active_work_location_label`
- `last_active_work_location_id`
- `last_active_work_location_label`
- `status_reason`

### Canonical status class

The stable class-level attendance state of the primary user attendance entity, such as signed in or signed out.

The canonical class set is:

- `signed_in`
- `signed_out`
- `unknown`

Work-location-specific meaning belongs in structured metadata or presentation, not in the canonical class set itself.

`unknown` means the integration cannot currently assert a trustworthy attendance class.

That may be due to backend unavailability or unresolved semantic ambiguity. The reason should be exposed through structured metadata or diagnostics, not by expanding the canonical class set.

The initial `status_reason` vocabulary should remain small and operational:

- `backend_unavailable`
- `target_not_configured`
- `target_temporarily_unusable`
- `routing_ambiguous`
- `missing_location_context`
- `backend_contract_mismatch`

### Available target state

A configured work-location-backed state that automation or manual actions can target.

Available target states are action choices, not separate primary attendance entities.

They support sign-in and sign-out verbs. They are not themselves a generic target-setting API.

Configured target state records should persist durable routing metadata, not transient backend state.

Unselected backend-discovered work locations should not be persisted as durable configuration.

They may be rediscovered later during configuration or reconfiguration.

The configured set of available target states is authoritative.

Attendance routing may narrow within that set at action time, but must not invent targets outside it.

Inclusion in the configured target set is a config-time decision.

Runtime observations may mark a configured target as temporarily unusable or invalid, but should not silently disable it in durable configuration.

Temporary runtime invalidity should be surfaced operationally, not rewritten into durable config.

### Signed-out state

The absence of any active work location in the primary user attendance entity.

It is not itself a configured work-location target state.

When signing out without explicit target input, inference should recover the previously active signed-in work location in order to exit it safely.

### Site

The Sign In App API term for a work location.

### Office location

A work-location mode where attendance actions depend on meaningful location coordinates.

### Remote location

A work-location mode where attendance actions do not require real-world coordinates in the same way as an office location.

### Contract drift

A meaningful mismatch between persisted routing semantics and later backend-discovered hints.

Contract drift should be surfaced through an admin-facing signal and resolved through reconfiguration.

It should not silently rewrite durable configuration.
