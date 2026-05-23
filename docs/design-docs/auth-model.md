# Auth Model

## Desired end state

Authentication should behave as a narrow, explicit capability grant:

1. user provides a companion code
2. integration exchanges it for a bearer token
3. token is used only for the minimal mobile-backend operations the integration needs
4. token refresh behavior is understood and documented

## Verified principles

- companion codes are normalized before exchange
- `POST /connect` returns a bearer token
- authenticated browser traffic uses that bearer token against `/api/mobile/*`
- `GET /reconnect` exists and returns a fresh token

## Known weaknesses

- repository code does not model reconnect explicitly
- request headers emulate a client fingerprint that can drift
- no fixture-backed auth contract tests exist yet

## Documentation rule

When auth behavior is observed, document:

- the endpoint
- the minimal required request shape
- the minimal relied-on response shape
- the security implications

Do not document secrets themselves.
