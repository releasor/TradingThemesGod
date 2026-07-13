# Bug Verification Guidance

## Verification Defaults

All bug fixes need verification that matches severity, reproduction clarity, and risk.

| Severity | Default verification expectation | Rationale |
|---|---|---|
| critical | Automated or hybrid verification with explicit regression coverage | Crash/data-loss/security bugs need durable proof. |
| high | Automated or hybrid verification for the broken core path | Core-feature failures need regression protection. |
| medium | Focused automated or manual verification | Workaround cases need proof without over-scoping. |
| low | Smallest meaningful check | Cosmetic or minor edge cases should stay lightweight. |

## Verification Type

- `automated`: use when a unit, integration, or E2E test can reliably reproduce the bug and prove the fix.
- `manual`: use when reproduction needs external state or human judgment and no stable automated check is practical.
- `hybrid`: use when automated regression coverage is possible but final confidence needs manual/browser confirmation.

## Browser Verification

Use `browser_interaction` for UI-reproducible bugs.

- `tool: auto` lets the runtime choose the best browser tool.
- `tool: playwright-cli` is best for local dev-server verification in an isolated browser.
- `tool: opencli` is best when an existing Chrome login/session or third-party integration cookies are needed.
- `verify_steps` should describe what to prove, not low-level click scripts.

Do not emit `critic` or `critic_count`; those fields are retired and validators reject them.
