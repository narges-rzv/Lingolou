# Viral Sharing Strategy

> Goal: make Lingolou stories effortless to share across every channel, and make each
> share pull new users back in. This is the foundation that the eventual mobile app
> (see below) will amplify — not replace.

## Where we are today (audit, 2026-06-05)

- There **is** a social/public layer already: public story library, voting, follows,
  bookmarks, worlds, timeline, blocks, `share_code` on stories and worlds, public
  unauthenticated read endpoints (`webapp/api/public.py`).
- There is **no share UI**: `/share/:shareCode` route exists (`SharedStoryView.tsx`) but
  nothing in the app generates, copies, or surfaces a share link. No native share sheet.
- There are **no Open Graph / Twitter Card meta tags**: the SPA catch-all
  (`webapp/main.py:155 serve_spa`) returns a static `index.html` with only
  `<title>Lingolou</title>`. Social crawlers don't execute JS, so every pasted link
  unfurls blank. **This is the #1 virality blocker.**
- No share image generation, no video/clip export, no embed, no referral attribution.

## Decisions (locked 2026-06-05)

- **Target channels: all four** — parent-to-parent (WhatsApp/iMessage), discovery
  (TikTok/Reels/Shorts), communities (Reddit/Pinterest/teachers), and search (SEO).
  Phase 1 is a prerequisite for all four, so it's pure shared foundation — nothing wasted.
- **Build order: Phase 1 foundation first**, ship it, then Phase 2 clips, then Phase 3 loop,
  then mobile.

## Strategic principle

Virality = (great-looking share) × (low friction to share) × (a loop that returns).
We are currently failing the first two and have no loop. Fix in that order. Mobile is a
distribution *amplifier* (native share sheet, save-to-camera-roll), so it comes after the
sharing primitives exist — otherwise we'd build them twice.

The single highest-leverage channel for an **audio storytelling** product in 2026 is
short vertical video (TikTok / Reels / Shorts). That's Phase 2 and is the real growth
engine. Phase 1 is table stakes that unblock every channel at once.

---

## Phase 1 — Make every link beautiful & shareable (foundation, mobile-agnostic)

Highest ROI. Cheap. Unblocks iMessage, WhatsApp, Discord, Slack, X, Facebook, LinkedIn,
Reddit, Telegram all at once.

1. **Server-rendered Open Graph / Twitter Card meta tags.**
   - In `serve_spa` (and `/share/...`, `/public/stories/...` routes), when the path is a
     shareable resource, read the story/world from DB and inject `<meta>` tags into the
     `index.html` shell before returning: `og:title`, `og:description`, `og:image`,
     `og:type`, `og:url`, `twitter:card=summary_large_image`, language/locale tags.
   - Inject for all requests (not just crawlers) — simpler, and harmless for real users
     since React still hydrates. Avoids fragile user-agent sniffing.
   - Tests: assert the HTML for `/share/{code}` contains the story title + og:image.

2. **Dynamic share images (OG image per story).**
   - Endpoint e.g. `GET /public/stories/{id}/og-image.png` that renders a 1200×630 card:
     cover art / illustration, story title, source→target language badge (e.g. 🇬🇧→🇪🇸),
     "Listen free on Lingolou" CTA. Cache to disk/Azure Files (same pattern as audio).
   - Start with a simple Pillow/HTML-to-image template; iterate on design later.

3. **Share UI in the app.**
   - A reusable `ShareButton` component on story detail, public detail, and shared view.
   - Uses Web Share API (`navigator.share`) when available (mobile browsers + future
     Capacitor native sheet), falls back to copy-link + per-channel buttons
     (WhatsApp, X, Reddit, email, QR code).
   - Auto-generate/ensure a `share_code` on first share if the story is link-shareable.

4. **QR code** for a story link — classroom / offline / parent-to-parent sharing.

## Phase 2 — The viral content engine: shareable clips (growth driver)

This is what actually spreads on social. An audio app is perfectly positioned: we already
have audio (`Chapter.audio_path`) + the script text (`script_json`).

5. **Auto-generated vertical video / audiogram clips (9:16, 15–40s).**
   - Pick a highlight passage (first exchange, or user-selected line range).
   - Render MP4: cover background + animated captions synced to audio (karaoke-style,
     dual-language), language badge, and a **"Made with Lingolou" watermark + CTA**.
   - Backend job (ffmpeg) reusing the existing BackgroundTasks + task_store progress
     pattern. Output downloadable + shareable.
   - This is the unit that gets posted to TikTok/Reels/Shorts and drives discovery.

6. **One-tap "Share clip"** from the audio player → native share sheet / download →
   user posts it. Watermark + CTA is the inbound funnel.

## Phase 3 — Close the loop (compounding growth)

7. **Referral attribution.** Append `?ref=<user/share_code>` to shared links; on signup,
   credit the referrer (e.g. bonus free-tier stories — ties into existing
   `free_stories_used` / `PlatformBudget`). Turns sharing into a self-interested act and
   gives a measurable K-factor.

8. **Embeddable player.** `GET /embed/story/{code}` iframe for blogs, Notion, forums,
   language-teacher sites. Long-tail SEO + reach into education communities.

9. **Public SEO surface + sitemap.** Server-render public story pages enough for Google
   to index titles/descriptions; generate `sitemap.xml` from public stories. Organic
   discovery for "free [language] story for kids" searches.

10. **Channel-tuned presets** once data shows what converts:
    - WhatsApp / iMessage → parents & family (rich preview + audio file). Likely top channel.
    - TikTok / Reels / Shorts → discovery (clips).
    - Reddit (r/languagelearning, parenting) / Pinterest (teachers) → cover cards + embed.

## Mobile app (Capacitor) — amplifier, built on top of the above

- Wrap the existing React/Vite frontend in Capacitor → real iOS/Android store apps,
  reusing the web codebase 1:1. See earlier discussion; details to go in
  `plans/mobile-app.md`.
- Mobile *inherits* all the sharing primitives and adds: native OS share sheet,
  save-clip-to-camera-roll, app deep links from shared URLs, and (later) push for
  follows/new-chapter notifications.
- OAuth redirect + WebView file download need Capacitor-specific handling (browser
  plugin, filesystem/share plugins).

## Phase 1 — status: BUILT (2026-06-05), not yet released

Implemented in this branch (all with tests, `make lint` + full suite green):
- OG/meta injection: `webapp/services/social_meta.py`, wired into `_serve_spa_shell`
  in `webapp/main.py` (root + catch-all). Injects per-story tags for `/share/{code}`
  and `/public/stories/{id}`, default brand tags elsewhere.
- Dynamic OG images: `webapp/services/social_image.py` (Pillow, 1200×630 cards),
  endpoints `GET /api/public/og-image.png` and `/api/public/stories/{id}/og-image.png`.
- `ShareButton` (`frontend/src/components/ShareButton.tsx`): native share sheet +
  copy-link + WhatsApp/X/Reddit/Facebook/email + QR (`qrcode` npm dep). Placed in
  `PublicStoryDetail` (also covers `SharedStoryView`).
- Tests: `webapp/tests/test_social_share.py` (16), `ShareButton.test.tsx` (6).
- Docs: README features + `PUBLIC_BASE_URL` env var. New dep: `pillow` in requirements.

Remaining for Phase 1 polish (optional follow-ups):
- Cache rendered OG images to storage instead of rendering per request.
- Set `PUBLIC_BASE_URL` in the k8s secret/config for production unfurls.
- 1e: verify real unfurls (X validator, FB debugger, paste into WhatsApp/iMessage).
- Surface ShareButton on the owner's private `StoryDetail` once a "make shareable"
  (generate share_code / set link_only) action exists.

## Phase 1 — concrete build breakdown (original)

Ordered so each step is independently shippable and testable.

- **1a. OG/meta injection (backend).** Add a helper that, for a shareable path
  (`/share/{code}`, `/share/world/{code}`, `/public/stories/{id}`...), loads the resource
  and returns `index.html` with injected `<meta>` tags (og:title/description/image/url/type,
  twitter:card, og:locale). Inject for all requests (no UA sniffing). Touches
  `webapp/main.py serve_spa`. Tests: HTML for a share URL contains title + og:image;
  unknown code falls back to default tags.
- **1b. Dynamic OG image (backend).** `GET /public/stories/{id}/og-image.png` →
  1200×630 card (cover/illustration, title, 🇬🇧→🇪🇸 language badge, "Listen free on
  Lingolou"). Pillow template to start; cache to disk/Azure Files like audio. Wire its URL
  into 1a's og:image. Tests: returns image/png, 200 for public story, 404 for private.
- **1c. ShareButton (frontend).** Reusable component: `navigator.share` when available,
  else copy-link + WhatsApp/X/Reddit/email buttons + QR. Place on StoryDetail,
  PublicStoryDetail, SharedStoryView. Ensures a `share_code` exists on first share.
  Tests: renders, copy-link writes URL, falls back when `navigator.share` absent.
- **1d. QR code.** Generate from the share URL (client lib or backend endpoint) for
  classroom/offline/parent-to-parent. Tests with 1c.
- **1e. Verify previews** with real unfurlers (X card validator, Facebook debugger,
  paste into WhatsApp/iMessage/Discord) before calling Phase 1 done.

Each sub-step ships with tests in the same commit (per CLAUDE.md) and updates README.

## Recommended sequence

1. Phase 1 (OG meta + share images + ShareButton + QR) — do first, ~highest ROI.
2. Phase 2 (clip generation) — the real growth engine; bigger build.
3. Phase 3 (referral loop, embed, SEO/sitemap) — compounds once 1 & 2 ship.
4. Mobile (Capacitor) — once sharing primitives exist, so the app inherits them.

## Open decisions

- Clip rendering: server-side ffmpeg (consistent, costs CPU) vs. client-side (free, but
  heavy in a WebView). Leaning server-side, reusing the audio job pattern.
- OG image rendering: Pillow template vs. headless-browser HTML render (nicer, heavier).
- Referral incentive: bonus free stories vs. cosmetic/world perks.
