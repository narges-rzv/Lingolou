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

## Phase 2 — The viral content engine: shareable clips (growth driver) — NEXT

This is what actually creates *cold-audience* reach. Phase 1 made sharing not-broken, but
it still depends on a user already having an audience. Clips are the unit that gets posted
to TikTok / Reels / Shorts and reaches strangers. An audio app is perfectly positioned.

**Key de-risker (confirmed in code):** chapters already store **per-line audio**
(`Chapter.line_audio_json` → `{ "0": "42/ch1/line_0.mp3", ... }`, plus
`Chapter.audio_duration` and a `has_line_audio()` helper, served via
`GET /api/.../lines/{i}/audio`). So caption↔audio sync is line-accurate for free: each
caption is shown for exactly its own line-audio segment's duration. No word-level
alignment needed for v1. This collapses the biggest technical risk.

**Biggest remaining risk:** font coverage. 35+ languages include CJK, Arabic (RTL),
Devanagari, Thai, etc. Burned-in captions need fonts that cover the target script →
bundle the Noto family and render via libass. Treat this as the first spike.

### Phase 2 build breakdown (sequenced, each independently testable)

- **2.0 Instrument first (small, do up front).** Add lightweight event counters for
  share-button opens, per-channel clicks, and (later) clip creations, so we can measure
  whether Phase 1 sharing is even used and which of the 4 channels converts. A tiny
  `ShareEvent`/counters table or append-only events. Data-drives every later decision.
- **2a. Caption + timing model.** From a chosen line range, read each line's text from
  `enhanced_json`/`script_json` (confirm the line schema: target-language text vs.
  translation fields) and each line's audio duration (ffprobe on the per-line segment,
  or proportional fallback if a segment is missing). Produce an `.ass` subtitle with
  per-line `[start,end]`. Dual-language layout: target text large, translation below.
- **2b. Font + render spike (the risk).** Bundle Noto fonts in the image; render a 9:16
  1080×1920 MP4 with ffmpeg + libass burning the `.ass` over a background, muxed with the
  concatenated per-line audio. Verify a non-Latin script (e.g. Persian/Hindi) renders.
- **2c. Visual template.** Background = brand gradient / OG-style card (reuse
  `social_image` aesthetic) for v1; a **"Made with Lingolou · lingolou.app" watermark +
  CTA** burned in every frame (this is the funnel). Animated background / per-story art =
  later.
- **2d. Render service + job + cache.** `webapp/services/clip.py` orchestrated via the
  existing BackgroundTasks + `task_store` progress pattern (same as audio). ffmpeg is
  already a runtime dep (used by combined-audio download). Cache output to storage keyed
  by `(story_id, chapter, line_range, template_version)`; serve via signed URL / download.
  Guard concurrency — the prod pod is single-replica with a 1-CPU limit, so a 1080p encode
  is heavy; serialize/queue clip jobs and consider it when sizing.
- **2e. API.** `POST /api/.../chapters/{n}/clip` (start job → task id),
  clip-status (reuse task progress), and `GET /api/public/stories/{id}/clip.mp4` for
  public stories. Line-range + caption-style in the request body.
- **2f. Frontend.** "Create clip" on the story/chapter view, a preview modal (video +
  download + reuse `ShareButton`/native share / save-to-camera-roll), and `TaskProgress`
  for the render. Default passage = first exchange; allow line-range selection.

### Phase 2 open decisions
- Caption fidelity: line-level (free, from per-line audio — recommended for v1) vs.
  word-level karaoke (needs ElevenLabs char alignment; nicer; later).
- Where rendering runs: in-pod ffmpeg with a concurrency guard (simplest, MVP) vs. a
  dedicated worker/Job (scales; more infra). Start in-pod; revisit if it competes with
  story/audio generation for the single CPU.
- Background visuals: static brand/OG card (v1) vs. animated gradient vs. AI art (later).
- Clip length & passage: auto first-exchange vs. user-selected range vs. "best line".

## Phase 3 — Close the loop (compounding growth)

Compounds once 2 ships and clips are circulating with the CTA.

- **3a. Referral attribution + reward (K-factor).** Append `?ref=<code>` to all shared
  links and clip CTAs (code = a per-user referral code; add column or reuse `public_id`).
  Store `ref` on landing (localStorage); attribute on signup via a `Referral` table
  (referrer, referred, created_at). Reward = bonus free stories (new `referral_credits`
  column or bump the per-user allowance; ties into `free_stories_used` / `PlatformBudget`).
  **Needs an Alembic migration.** Anti-abuse: self-referral guard, one credit per verified
  new user. UI: a "Refer a friend" page (link + credits earned) in Settings/Dashboard.
- **3b. Embeddable player.** `GET /embed/story/{code}` → minimal chrome-less HTML page
  (player + title + "Listen on Lingolou" link), iframe-friendly headers (allow framing /
  relaxed CSP for this route only). Optional `oEmbed` endpoint so platforms auto-embed.
  Reach into teacher blogs, Notion, forums.
- **3c. SEO surface + sitemap.** Extend the Phase 1 server-rendered shell so public story
  pages expose indexable content (e.g. a `<noscript>` summary: title, description, first
  lines). Generate `GET /sitemap.xml` from public stories + `robots.txt`. Targets
  long-tail "free [language] story for kids" searches. Per-language landing pages = later.
- **3d. Channel-tuned presets** (driven by the 2.0 analytics):
  - WhatsApp / iMessage → parents & family (rich preview + audio file) — likely top channel.
  - TikTok / Reels / Shorts → discovery (clips).
  - Reddit (r/languagelearning, parenting) / Pinterest (teachers) → cover cards + embed.

## Phase 4 — Mobile app (Capacitor) — amplifier, built on top of the above

Detailed plan: `plans/mobile-app.md`. Summary:
- Wrap the existing React/Vite frontend in Capacitor → real iOS/Android store apps,
  reusing the web codebase 1:1.
- Mobile *inherits* all the sharing primitives for free — `ShareButton` already calls
  `navigator.share`, which maps to the native OS share sheet inside the Capacitor WebView.
  Adds: save-clip-to-camera-roll (Filesystem/Media plugins), app deep links from shared
  https URLs (universal links / app links), and (later) push for follows/new chapters.
- Build/release needs: Apple Developer Program ($99/yr, requires a Mac + Xcode), Google
  Play ($25 one-time). OAuth redirect needs in-app handling (Browser plugin + custom
  scheme). WebView audio background playback may need a native plugin.

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

## Recommended sequence & status

1. ✅ **Phase 1** (OG meta + share images + ShareButton + QR) — SHIPPED in v1.1.7
   (2026-06-05). Remaining: verify real unfurls in prod; optional OG-image caching.
2. ⏭️ **Phase 2** (clip generation) — NEXT. The real growth engine. De-risked by
   per-line audio; main risk is multi-language font coverage. Start with 2.0 analytics +
   the 2b font/render spike.
3. **Phase 3** (referral loop, embed, SEO/sitemap) — compounds once clips circulate.
   Begin once Phase 2 is live and the 2.0 analytics show which channels convert.
4. **Phase 4 — Mobile** (Capacitor) — last, so the app inherits all sharing primitives.

### What's next, concretely
- **This week:** confirm Phase 1 unfurls render in prod (X validator, FB debugger,
  WhatsApp/iMessage). Land the small **2.0 analytics** so we can measure share usage.
- **Then:** the **Phase 2b font/render spike** — prove a 9:16 captioned MP4 renders for a
  non-Latin language. That single spike validates the whole clip engine; everything else
  in Phase 2 is plumbing around it.
