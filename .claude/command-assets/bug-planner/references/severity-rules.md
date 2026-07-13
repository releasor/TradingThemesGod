# Severity Auto-Classification Rules

When extracting bugs, apply these rules to auto-suggest severity. Require a short rationale for every severity assignment and then map severity to priority using the planner's preserved mapping.

| Severity | Indicators | Examples |
|----------|------------|----------|
| **critical** | System-wide crash, active data loss/corruption, exploitable security breach, OOM, unrecoverable production outage, no workaround | `Segmentation fault` on startup, `OutOfMemoryError` halting workers, `SQL injection vulnerability`, `Database corrupted` |
| **high** | Core feature outage, authentication/authorization failure, data integrity issue, repeated timeout/crash/500 on primary workflow, payment blocked, no reasonable workaround | `Auth token invalid for all users`, `Payment failed for valid cards`, `Connection timeout on checkout`, `500 Internal Server Error on login` |
| **medium** | Feature partially broken, incorrect output, validation gap, failed non-critical test, workaround exists, limited user segment affected | `CSV encoding issue with manual export workaround`, `Pagination not working on admin table`, `Wrong date format`, `Missing optional validation` |
| **low** | Cosmetic issue, minor inconvenience, rare edge case with easy workaround, non-breaking warning, docs/copy issue | `UI misalignment`, `Typo in error message`, `Slow loading on non-critical page`, `Non-breaking warning` |

## Special Cases

- Failed test → medium unless the failed test covers auth, payment, data integrity, security, startup, or another critical path; then high with rationale.
- User report with "cannot use app" → high only when a primary workflow is blocked and no workaround exists.
- User report with "annoying but works" → low.
- User frustration, repeated wording, or "please fix urgently" is not a severity indicator by itself; look for objective impact.
- Framework or infrastructure bugs are not automatically high; classify by user/runtime impact and workaround availability.

## Mixed Calibration Examples

| Bug | Severity | Priority | Rationale |
|-----|----------|----------|-----------|
| Login returns 500 for every valid credential | high | high | Core auth workflow outage with no workaround; high severity maps to high priority. |
| CSV export corrupts non-ASCII characters but JSON export works | medium | medium | Incorrect output with a workaround; medium severity maps to medium priority. |
| Settings tooltip has outdated wording | low | low | Cosmetic copy issue only; low severity maps to low priority. |

Anti-pattern: do not generate an all-high bug list unless each bug independently includes high/critical indicators such as core outage, data loss/integrity, security/auth failure, timeout/crash, or no workaround.
