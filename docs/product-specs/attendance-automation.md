# Attendance Automation

## Product statement

Home Assistant should be able to express a user's attendance through Sign In App without requiring the user to open the companion app, including sign-in and sign-out across the user's supported work locations.

## Primary user journey

1. User connects the integration with a companion code.
2. User configures the work locations the integration should manage from the locations available to them in Sign In App.
   - backend-discovered names are prefilled where possible
   - user labels can override backend names
   - stable backend identity remains the routing and entity key
   - backend-discovered routing hints are presented and confirmed during config flow
   - explicit inclusion decides which discovered work locations become available target states
3. User selects the Home Assistant `person` entity representing them.
4. Home Assistant automations or manual actions call:
   - `signinapp.sign_in` for the relevant work location context
   - `signinapp.sign_out` when leaving work context
5. Home Assistant displays current status through the integration sensor.

Sign-in and sign-out remain distinct verbs in the product model. They do not collapse into a generic attendance-target setter.

## Entity model

- one primary user attendance entity represents the user's overall Sign In App state
- canonical status classes define the core state machine of that entity
- the canonical class set is `signed_in`, `signed_out`, and `unknown`
- `unknown` means the integration cannot currently assert a trustworthy attendance class, with reason exposed through attributes or diagnostics
- active and last-active work-location identity and label belong in structured attributes when available
- last-active context is operational and supports sign-out inference and post-sign-out interpretation
- available target states define the configured work locations that actions can target
- configured work locations are not separate primary attendance entities
- configured available target states define the authoritative action-target universe
- configured target records persist durable routing metadata, not transient backend state
- the minimum durable routing metadata per configured work location is stable backend identity, user label, inclusion state, coordinate-behaviour semantics, and any required location-specific parameter
- the current coordinate-behaviour set is limited to `device_tracker` and `remote_zero` unless a concrete new Sign In App scenario requires another mode
- unselected discovered work locations are rediscovered later rather than stored as durable shadow configuration
- signed out is absence of an active work location, not another configured target state
- backend drift does not silently rewrite durable config; it is surfaced to an administrator and resolved in reconfiguration

The primary entity should expose structured attributes for:

- `status_class`
- `active_work_location_id`
- `active_work_location_label`
- `last_active_work_location_id`
- `last_active_work_location_label`
- `status_reason`

The initial operational `status_reason` set is:

- `backend_unavailable`
- `target_not_configured`
- `target_temporarily_unusable`
- `routing_ambiguous`
- `missing_location_context`
- `backend_contract_mismatch`

## Required product outcomes

- attendance routing uses the correct location semantics for the resolved target
- attendance routing applies explicit action input first, then live backend state, then cached local session state as fallback
- sign-in remains explicit-first, while sign-out may infer the active work location when explicit input is absent
- sign-in and sign-out remain distinct verbs with different routing behaviour
- explicit action input can transition from routing hints towards concrete work-location identity
- compatibility hints remain supported, but concrete work-location identity is the primary product surface
- the transition action surface supports concrete work-location identity first, then sign-out inference without explicit target, then routing-hint compatibility inputs
- concrete-target actions fail when the chosen configured target is temporarily unusable
- cross-target fallback is reserved for hint-level actions and explicit routing policy
- configuration flow makes location selection first-class rather than implicit or hand-entered
- configuration flow seeds names from backend data but permits user override
- configuration persists durable routing metadata per configured work location
- routing semantics are confirmed during config flow, not edited during each action
- unselected discovered work locations are rediscovered during later config rather than persisted as durable configuration
- mutable labels improve UX but do not drive attendance routing
- one primary user attendance entity remains the main user-facing state surface
- canonical status classes remain stable even when work-location labels change
- work-location-specific meaning is exposed as metadata or presentation, not as new canonical classes
- available target states exist for action targeting across configured work locations
- attendance routing may narrow within configured targets but must not invent targets outside them
- sign-out inference recovers the previously active signed-in work location when explicit target input is absent
- sign-out targets the correct work location even if backend status is sparse
- sensor state reflects the best known true state

## Failure cases that matter

- wrong work location selected for sign-out
- stale sensor state after restart
- backend current-site field changes and integration silently guesses
- setup succeeds but later automation behaviour is unreliable

## Reconfiguration behaviour

When backend-discovered routing hints change later, the integration should preserve user-confirmed durable routing semantics by default.

The system should:

- raise an admin-facing issue when meaningful drift is detected
- resolve drift through reconfiguration rather than silent mutation
- present current configured label and routing semantics beside newly discovered backend hints
- allow the user to keep the current configuration, accept the discovered hints, or edit the user-facing label
