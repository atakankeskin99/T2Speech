# Interactive demo v0.1

The static demo lets visitors try Library → Deck → Study Setup → Study Mode →
Session Complete with three read-only sample decks. It uses the production UI
stylesheet and theme script. It requires no FastAPI process, database, account,
frontend framework, JavaScript dependency installation, or compilation step.

## Files and reuse

```text
demo/
  index.html
  deck.html
  study_setup.html
  study.html
  study_complete.html
  css/demo.css
  data/sample-decks.json
  js/demo-app.js
  js/demo-session.js
  js/demo-storage.js
  js/demo-study.js
scripts/prepare_demo.py
tests/demo/session.test.cjs
tests/demo/test_static_demo.py
.github/workflows/demo-pages.yml
```

The provisional structure gained `demo-study.js` to keep Study Mode interactions
separate from page navigation, and a small stylesheet for demo notices and hidden
states. The five HTML pages retain production CSS classes, reading surfaces,
settings popover, completion layout, and audio icons. CRUD/import/export controls
are absent because sample data is read-only.

Inspection found that `app/static/js/study.js` submits ratings and settings to
FastAPI and assumes server-rendered session state. Loading it unchanged would
make the demo call production endpoints. Its interaction conventions are adapted
in `demo-study.js`; the Python session engine and production assets are unchanged.
The shared `app.js` theme logic is safe to reuse because its other behaviors are
guarded by the presence of production CRUD controls.

`scripts/prepare_demo.py` copies an explicit list of public demo files and the
unchanged production `app.css` and `app.js` into `build/demo/assets/`. There are no
tracked copies of shared assets. Packaging never imports the Python application,
opens SQLite, or copies `data/`, `.env`, or distribution files. It rejects existing
artifact directories containing unexpected files. Re-run it after source changes.

## Local preview and checks

From the repository root, using Python 3.10+:

```powershell
python scripts/prepare_demo.py
python -m http.server 8000 --directory build/demo --bind 127.0.0.1
```

Open `http://127.0.0.1:8000/`. This is a static file server, not an application
backend. Opening source HTML through `file://` is unsupported because browsers
restrict fetching the sample JSON. To preview the project subpath, package with
`--output build/pages/T2Speech` and serve `build/pages`; open `/T2Speech/`.

```powershell
node --test tests/demo/session.test.cjs
python -m pip install -r requirements.txt -r requirements-test.txt
python -m playwright install chromium
python -m pytest tests -q
```

Node is needed only for deterministic queue tests; visitors do not need it.
Browser tests serve a real packaged artifact under `/T2Speech/` and check that
every request is a GET inside that static directory. They cover sample data,
keyboard reveal/ratings, duplicate ratings, Again ordering, resume, replacement,
abandonment, completion, immediate settings, validation, timer cancellation, TTS
failure, theme continuity, direct navigation, refresh, storage recovery, and
320/390/768/1024/1440 px layouts. Chromium tests skip if Playwright or its browser
is unavailable; an all-green run with skips is not full browser validation.
Tests use isolated temporary files and never access the user's deck database.

## Session contract and limitations

Each session contains card text and language snapshots, options, settings, a
pending ID queue, a revision, reveal state, and status. The first pending ID is the
current card. Completed count is `cards.length - pending.length`; progress is that
count divided by `cards.length`. No extra count or active-session index is stored.
Again removes the head and reinserts at `min(3, remaining.length)`. Good removes
the head permanently. A rating needs reveal, the current card ID, and the exact
revision, preventing duplicate submission even with a one-card Again loop.

One session per deck can be active. Replacement confirmation captures that
session's ID; replacement marks it `abandoned`. Only an empty pending queue after
Good produces `completed`. Direct completion links reject active, abandoned, and
missing sessions. Snapshot text, pending order, settings, Shuffle/Reverse, current
card, and reveal state survive refresh and navigation within the same tab.

Storage is `sessionStorage`, limited to the browser tab/session. Browser session
restoration may retain it; new/duplicated tabs may receive an initial browser copy
but do not synchronize. It is not the desktop application's durable SQLite
persistence. Storage being blocked/full is reported as a browser storage problem;
writes must succeed before in-memory progress commits. Corrupt saved data offers
an explicit reset with confirmation. Light/Dark uses the existing localStorage
theme preference and survives across pages when that storage is available.

Settings default to auto-speak Off, rate 1, auto-reveal Off, and delay 5 seconds.
Valid settings save immediately to the active session. Invalid numeric input
keeps the previous committed value. As in production, changing auto-speak affects
the next face/card rather than playing immediately. Auto-reveal timers and speech
are cleared on card advance and navigation. Space reveals, 1 rates Again, 2 rates
Good, R repeats the last audio, and Escape closes settings or returns to the deck.
Shortcuts ignore editors, interactive controls, held keys, and modifier keys.

Speech uses the browser Web Speech API, prefers a matching installed local voice,
respects the displayed face's language in Reverse mode, and applies the session
rate (0.1–10). Voice availability and autoplay policies vary by browser/OS;
Play front/Play answer can start playback after a user gesture. No remote voice
fallback, cloud TTS credential, or identical cross-platform speech is promised.
Missing/failing speech never prevents studying. Automated tests stub speech;
real audible playback and Safari/Firefox require separate device verification.

This is an interactive sample-data demonstration, not feature parity with the
desktop application. Deck/card editing, import/export, accounts, and durable
personal libraries are outside its scope.

## GitHub Pages deployment

Target after a successful deployment: `https://atakankeskin99.github.io/T2Speech/`.
All application navigation and asset URLs are relative. Physical HTML files plus
query parameters support refresh and direct navigation without rewrite rules.

The workflow runs only for relevant pushes to `main`, packages `demo/` with its
shared assets, and uploads that directory rather than the whole repository.
It has no feature-branch, pull-request, or manual deployment trigger. Deploy
depends on packaging and has `pages: write` and `id-token: write` permissions in
the `github-pages` environment. This follows the
[GitHub custom Pages workflow requirements](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

An administrator must first enable repository Settings → Pages → Source → GitHub
Actions, and allow `main` in the `github-pages` environment protection rules.
The workflow does not assume Pages is enabled or enable it automatically.
No custom domain is configured. A push to the feature branch does not publish the
demo. After merging, check the workflow result and visit the target URL before
claiming that the site is live.
