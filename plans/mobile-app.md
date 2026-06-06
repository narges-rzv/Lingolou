# Mobile App Plan (Capacitor) — Phase 4

> Build *after* the sharing phases (see `plans/viral-sharing.md`), so the app inherits
> the OG previews, ShareButton, and clip engine rather than rebuilding them. Mobile is a
> distribution *amplifier*, not the strategy.

## Why Capacitor

The frontend is already React 18 + Vite + TypeScript talking to FastAPI over HTTP.
Capacitor wraps that exact built bundle (`webapp/static/frontend` / `frontend/dist`) in a
native WebView, producing real `.apk` / `.ipa` apps for both stores from one codebase.
The backend doesn't change — the app points at `https://www.lingolou.app`. Chosen over a
PWA (iOS is hostile to background/locked-screen audio, which is core here) and over React
Native (which would mean rewriting every page).

## What it inherits for free

- **Sharing:** `ShareButton` already calls `navigator.share` → the native OS share sheet
  works inside the Capacitor WebView with no change.
- **Rich link previews:** server-rendered OG tags work regardless of client.
- **Clips (once Phase 2 ships):** the share/download flow carries over.

## Build breakdown

- **4a. Scaffold.** `npm i @capacitor/core @capacitor/cli` in `frontend/`; `npx cap init`;
  `npx cap add ios` / `npx cap add android` (creates `ios/` and `android/` native
  projects). Point the app at the production API base instead of a bundled backend.
- **4b. Auth in-app.** Google OAuth's plain web redirect won't work in a WebView — use
  `@capacitor/browser` (system browser / ASWebAuthenticationSession) with a custom URL
  scheme / app deep link to receive the `?token=`. Adjust the redirect handling that today
  lives in `AuthContext` and `webapp/api/oauth.py` (`FRONTEND_URL` redirect).
- **4c. Audio.** Verify WebView `<audio>` handles background + lock-screen playback; if
  not, add a native audio plugin. This is the main product-critical mobile risk.
- **4d. Downloads / save-to-device.** Per-chapter audio downloads and (Phase 2) clip
  saves need `@capacitor/filesystem` + share/media plugins to land in Files / camera roll
  rather than a WebView blob download.
- **4e. Deep links.** Universal Links (iOS) / App Links (Android) so shared
  `https://www.lingolou.app/share/...` URLs open the app when installed.
- **4f. Store assets + submission.** Icons, splash, screenshots, privacy labels, listing.
- **4g. (Later) Push notifications** for follows / new chapters via `@capacitor/push-
  notifications` + a backend send path.

## Prerequisites / costs

- **Apple Developer Program** — $99/yr; building iOS requires a Mac + Xcode.
- **Google Play Developer** — $25 one-time.
- App Store review (privacy nutrition labels, account-deletion requirement, etc.).

## Open decisions

- Single shared bundle vs. light platform-specific tweaks (safe-area insets, native
  back-button handling on Android).
- OTA updates (e.g. Capacitor live-updates) vs. store-only releases.
- Whether to ship mobile before or after Phase 3 (referral loop) — leaning after, so the
  app ships with the full growth loop intact.
