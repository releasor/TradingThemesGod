# Plan Examples

## Example 1: New Feature

**Input:** "I want users to upload avatars"

**Phase 0 output:** `.prizmkit/specs/003-user-avatar/spec.md`
```markdown
# User Avatar Upload
## Overview
Allow registered users to upload and manage profile pictures.
## Goals
### G-1: Upload Avatar
As a registered user, I want to upload a profile picture,
so that other users can visually identify me.
**Acceptance Criteria:**
- Given I am on my profile page
- When I select an image file and click upload
- Then my avatar is updated and visible across the platform
## Scope
- **In scope:** Upload, display, remove avatar; image format validation
- **Out of scope:** Image cropping/editing, avatar history
```

**Phase 1-2 output:** `plan.md` excerpt:
```markdown
## Tasks
### Phase: Foundation (T-010~T-019)
- [ ] [T-010] [G-1] Add avatar_url field to User model — file: src/models/user.ts
- [ ] [T-011] [G-1] Create S3 upload utility — file: src/lib/s3.ts
### Phase: Core [P] (T-100~T-109)
- [ ] [T-100] [P] [G-1] POST /api/avatar upload endpoint — file: src/routes/avatar.ts
```

## Example 2: Refactoring

**Input:** "Extract shared auth middleware from the API routes"

**Phase 0 output:** `.prizmkit/specs/004-extract-auth-middleware/spec.md`
```markdown
# Extract Auth Middleware
## Overview
Consolidate duplicated authentication logic scattered across route files into a single shared middleware.
## Goals
### G-1: Extract Shared Authentication Logic
Consolidate duplicated auth checks from 5 route files into a single middleware module.
**Acceptance Criteria:**
- All existing auth-related tests pass without modification
- Auth logic exists in exactly one file (src/middleware/auth.ts)
- No route file contains inline token verification
## Scope
- **In scope:** src/routes/users.ts, orders.ts, admin.ts, payments.ts, profile.ts
- **Out of scope:** Authorization (role-based access), rate limiting
## Behavior Preservation
- All 23 existing API tests must pass unchanged
- Response formats and HTTP status codes must not change
- Error message strings must remain identical
```

## Example 3: Bug Fix

**Input:** "Login page crashes when API returns 401"

**Phase 0 output:** `.prizmkit/specs/005-login-401-crash/spec.md`
```markdown
# Fix: Login Crash on 401 Response
## Overview
Login page throws unhandled exception when auth API returns 401, causing a white screen.
## Goals
### G-1: Handle 401 Response Gracefully
When the auth API returns 401, display an error message instead of crashing.
**Acceptance Criteria:**
- Given user submits invalid credentials, When API returns 401, Then error message "Invalid credentials" is displayed
- Given user submits invalid credentials, When API returns 401, Then no unhandled exception is thrown
## Root Cause
- Error classification: Runtime
- Root cause: `AuthService.handleLogin()` at src/services/auth.ts:42 does not handle null token
- Affected files: src/services/auth.ts (L42), src/pages/login.tsx (L28)
## Scope
- **In scope:** Null handling in auth service, error display in login page
- **Out of scope:** Other HTTP error codes (403, 500), auth flow redesign
## Behavior Preservation
- All existing login success tests must pass unchanged
- Auth token flow for valid credentials must not change
```
