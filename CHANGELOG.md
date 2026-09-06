# Changelog

## 3.2.4 — Auth Integrations + Full Recheck
- Added production Google OAuth 2.0 authorization-code login.
- Added Telegram Login / OIDC authorization-code + PKCE.
- Added Telegram ID-token signature verification using Telegram JWKS.
- Added social-account linking to existing seller accounts by verified Google email.
- Added real SMTP password-reset email delivery via Nodemailer.
- Added hashed, expiring, single-use password-reset tokens.
- Password reset revokes existing seller sessions before creating the new secure session.
- Added OAuth state persistence/expiry and CSRF-resistant callback handling.
- Added Render/.env wiring for OAuth and SMTP secrets.
- Added reset-password UI and OAuth redirect handling.
- Re-ran Node/Python/frontend/static regression checks.
- Live provider login/email and Docker/Render runtime remain provider/infrastructure dependent.

# SHIVAM BOT BUILDER 3.2.3

- Rebuilt the first-visit authentication screen as a premium neon cyberpunk website UI inspired by the approved reference design.
- Added branded SHIVAM BOT BUILDER header/logo and animated circular shield HUD with orbiting dotted/line rings.
- Added Login mode with Username or Email, Password, Forgot Password, Telegram and Google buttons, plus Create Account navigation.
- Added Create Account mode with Username, Email Address, Password and Confirm Password fields plus social sign-up buttons.
- Added a very subtle floating/tilt animation to the main authentication card, with reduced-motion support.
- Added seller email persistence and username-or-email login support while preserving existing seller authentication.

# SHIVAM BOT BUILDER 3.1.1

- Deep audit pass over seller auth, bot lifecycle, product maintenance, payments, orders, members, broadcast, SaaS admin and UI navigation.
- Fixed admin wallet top-up lookup to use the Telegram user ID rather than the internal SQLite row ID.
- Fixed wallet top-up flow state to use gateway payment flow instead of legacy UTR flow.
- Added a real Super Admin UI for seller management, plans, invoices and commissions.
- Added client request timeout handling so a hung API request surfaces a clear error instead of a permanently dead-looking button.
- Kept product Maintenance toggle and gateway-only payment tracking.
## 3.2.5 — Premium Dashboard & Navigation
- Reworked the authenticated dashboard shell with a global three-dot menu and profile orb.
- Added dedicated Wallet, Top-up Payments, API/Payment Gateway and Protect/Security pages.
- Added Create Board navigation while preserving the existing bot deployment backend.
- Added dashboard quick actions, payment health, store snapshot and responsive mobile/desktop layouts.
- Converted the full seller navigation into a grouped slide-out drawer opened from the three-dot button.
- Kept login/OAuth/password-reset UI intact.
