# T2Speech — Interactive Demo

A browser-based, interactive preview of T2Speech's study experience, built with static HTML, CSS, JavaScript, and three read-only sample decks.

The demo walks through the complete **Library → Deck → Study Setup → Study Mode → Session Complete** flow. It reuses the production UI stylesheet and theme script while keeping demo-specific interactions separate from the FastAPI application.

> **Scope:** This is a sample-data demonstration, not a full browser edition of T2Speech. It does not provide a persistent personal library or feature parity with the desktop application.

## Try the Demo

**GitHub Pages deployment target:** [T2Speech Interactive Demo](https://atakankeskin99.github.io/T2Speech/)

The URL is the intended destination **after a successful deployment**. Repository administrators must enable GitHub Pages and verify the deployment before treating the site as live.

No account, FastAPI backend, database, frontend framework, JavaScript dependency installation, or compilation step is required to use the published demo.

## What You Can Explore

- **Library and decks:** Browse three read-only sample decks and open a deck.
- **Study setup:** Configure a session, including Shuffle and Reverse options.
- **Study Mode:** Reveal cards and rate them with **Again** or **Good**.
- **Session controls:** Resume sessions, confirm replacement of an active session, and review completion.
- **Session settings:** Configure automatic speech, speech rate, automatic reveal, and reveal delay.
- **Audio and themes:** Use browser-provided speech where available and switch between Light and Dark themes.

The demo retains the production UI's CSS classes, reading surfaces, settings popover, completion layout, and audio icons.

### Demo Limitations

| Demo behavior | Boundary |
| --- | --- |
| Three sample decks | Read-only data; no deck or card editing |
| Study sessions | Stored in browser `sessionStorage`, not SQLite |
| Library | No durable personal library or cross-tab synchronization |
| Import/export | Not included |
| Accounts | Not included |
| Text-to-speech | Browser Web Speech API; voices and behavior depend on browser/OS |

The demo intentionally omits CRUD and import/export controls. Browser speech is not guaranteed to sound or behave identically across platforms.

## Run Locally

From the **repository root**, with **Python 3.10+**:

```powershell
python scripts/prepare_demo.py
python -m http.server 8000 --directory build/demo --bind 127.0.0.1
```

Open <http://127.0.0.1:8000/> in a browser.

This serves static files only; it does not start FastAPI. Opening the source HTML using `file://` is unsupported because browser restrictions can prevent loading the sample JSON.

### Preview the GitHub Pages Subpath

To reproduce the `/T2Speech/` project path locally:

```powershell
python scripts/prepare_demo.py --output build/pages/T2Speech
python -m http.server 8000 --directory build/pages --bind 127.0.0.1
```

Open <http://127.0.0.1:8000/T2Speech/>. Navigation and asset URLs are relative; physical HTML pages and query parameters support direct navigation and refresh without rewrite rules.

## Technical Documentation

Expand the sections below for implementation details, testing, session behavior, browser support, and deployment.

<details>
<summary>Project Structure</summary>

Paths below are relative to the repository root:

```text
demo/
├── README.md
├── index.html
├── deck.html
├── study_setup.html
├── study.html
├── study_complete.html
├── css/
│   └── demo.css
├── data/
│   └── sample-decks.json
└── js/
    ├── demo-app.js
    ├── demo-session.js
    ├── demo-storage.js
    └── demo-study.js

scripts/
└── prepare_demo.py

tests/demo/
├── session.test.cjs
└── test_static_demo.py

.github/workflows/
└── demo-pages.yml
```

`demo-study.js` isolates Study Mode interactions from page navigation. `demo.css` contains demo notices and hidden-state styles.

### Production Asset Reuse

The production `app/static/js/study.js` submits ratings and settings to FastAPI and expects server-rendered session state. Including it unchanged would cause the static demo to call application endpoints, so its interaction conventions are adapted in `demo/js/demo-study.js` instead.

The demo reuses the production `app.css` and `app.js` without modifying them. The shared `app.js` theme logic can be reused because its other behaviors are guarded by checks for production CRUD controls. The Python session engine remains unchanged.

### Static Packaging

`scripts/prepare_demo.py` builds the deployable static site from an explicit allowlist of public demo files and copies the unchanged production `app.css` and `app.js` into the packaged `build/demo/assets/` directory. Shared assets are **not** maintained as tracked duplicate copies.

Packaging does **not**:

- Import or start the Python application.
- Open the SQLite database.
- Copy private `data/` content, `.env`, or distribution files.
- Accept unexpected files in an existing artifact directory.

Run the preparation script again after changing demo sources or shared production assets. The published artifact is the packaged output, not the entire repository.

</details>

<details>
<summary>Run Tests</summary>

Run the deterministic session-queue tests from the repository root:

```powershell
node --test tests/demo/session.test.cjs
```

To install the Python test requirements and Chromium for Playwright, then run the test suite:

```powershell
python -m pip install -r requirements.txt -r requirements-test.txt
python -m playwright install chromium
python -m pytest tests -q
```

Node.js is needed only for the deterministic queue tests; it is **not** required by demo visitors.

Browser tests serve an actual packaged build under `/T2Speech/` and verify that requests are **GET** requests confined to that static directory. The suite covers:

- Sample data and navigation, including direct URLs and refresh.
- Keyboard reveal and ratings, duplicate-rating protection, and Again ordering.
- Session resume, replacement, abandonment, and completion.
- Immediate settings changes, numeric validation, and timer cancellation.
- Speech failures and theme continuity.
- Browser storage recovery.
- Viewport widths of **320, 390, 768, 1024, and 1440 px**.

The tests use isolated temporary files and do not access a user's deck database. Chromium tests are skipped when Playwright or its browser is unavailable; **a passing run with skips is not full browser validation**. Automated speech tests use stubs, so audible playback and Safari/Firefox behavior still require checks on real devices.

</details>

<details>
<summary>Study Session Behavior</summary>

### Session State and Progress

Each session stores snapshots of card text and languages, options, settings, an ordered queue of pending card IDs, a revision number, reveal state, and status.

- The first pending ID identifies the current card.
- Completed count is `cards.length - pending.length`.
- Progress is `(cards.length - pending.length) / cards.length`.
- No redundant completed counter or active-session index is stored.

### Again, Good, and Duplicate Protection

- **Again:** Remove the current card from the front of the queue, then reinsert it at `min(3, remaining.length)` — after up to three other cards.
- **Good:** Remove the current card from the pending queue permanently for that session.
- **Rating validation:** A rating requires the card to be revealed, the current card ID to match, and the exact session revision. This prevents duplicate submissions, including one-card Again loops.

### Session Lifecycle

Only one session per deck may be active. Replacing one requires confirmation tied to that session's ID; the replaced session is marked `abandoned`. A session becomes `completed` only when a Good rating empties its pending queue. Direct completion links reject missing, active, and abandoned sessions.

Within the same browser tab, navigation and refresh preserve snapshot text, pending order, settings, Shuffle/Reverse, current card, and reveal state, subject to browser storage availability.

</details>

<details>
<summary>Browser Storage</summary>

Study session data uses **`sessionStorage`**, which is scoped to a browser tab/session. A browser may restore session storage after a restart, and newly opened or duplicated tabs may receive an initial copy, but tabs do not synchronize their session data.

This is distinct from the desktop application's durable SQLite persistence.

- When storage is blocked or full, the UI reports a storage problem.
- A storage write must succeed **before** the in-memory study progress is committed.
- Corrupt stored data offers an explicit reset requiring confirmation.
- Light/Dark theme preferences use the existing `localStorage` behavior and can persist across pages when storage is available.

</details>

<details>
<summary>Settings, Shortcuts, and Speech</summary>

### Default Session Settings

| Setting | Default |
| --- | --- |
| Auto-speak | Off |
| Speech rate | `1` |
| Auto-reveal | Off |
| Auto-reveal delay | `5 seconds` |

Valid changes save immediately to the active session. Invalid numeric input leaves the previously committed value unchanged. Changing auto-speak affects the **next face or card**, rather than triggering immediate playback. Auto-reveal timers and speech are cleared when advancing cards or navigating away.

### Keyboard Shortcuts

| Key | Action |
| --- | --- |
| `Space` | Reveal the current card |
| `1` | Rate **Again** |
| `2` | Rate **Good** |
| `R` | Repeat the last audio |
| `Escape` | Close settings or return to the deck |

Shortcuts ignore editable fields, other interactive controls, held keys, and modifier-key combinations.

### Text-to-Speech

Speech uses the browser's **Web Speech API** and prefers a matching locally installed voice. In Reverse mode it uses the language of the face currently displayed, with the session's speech-rate setting (`0.1–10`).

Browser and operating-system voice availability and autoplay rules differ. **Play front** and **Play answer** can initiate speech following a user gesture, but the demo does not promise a remote voice fallback, cloud TTS credentials, or identical speech across platforms. Missing or failed speech does not block studying.

</details>

<details>
<summary>GitHub Pages Deployment</summary>

The deployment workflow is defined in [`.github/workflows/demo-pages.yml`](../.github/workflows/demo-pages.yml).

It runs for relevant pushes to `main`, packages `demo/` with its required shared assets, and uploads **only the packaged site**, not the full repository. It does not deploy feature branches or pull requests, and it has no manual deployment trigger.

Deployment depends on the packaging job and uses `pages: write` and `id-token: write` permissions in the `github-pages` environment, following [GitHub's custom Pages workflow requirements](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

**One-time repository setup:** An administrator must configure **Settings → Pages → Source → GitHub Actions** and permit `main` through the `github-pages` environment protection rules. The workflow does not enable Pages automatically. No custom domain is configured.

A feature-branch push alone will not publish the demo. After merging into `main`, inspect the workflow result and open the deployment target to confirm the site is available before announcing it as live.

</details>

---

For the full application, see the [T2Speech repository README](../README.md).
