"""Optional browser-component tests using production templates, CSS and JS.

These deliberately mock only the Web Speech implementation and transport; all
settings requests still execute the REAL FastAPI route with an isolated DB.
They are not a substitute for a live HTTP/browser end-to-end test.
"""
from __future__ import annotations

from pathlib import Path
import os

import pytest
from bs4 import BeautifulSoup

from conftest import start_study

pytestmark = pytest.mark.browser


@pytest.fixture
def chromium():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as pw:
        launch_options = {"headless": True}
        # Optional override for CI environments using an already installed
        # Chromium. Ordinary Windows machines use Playwright-managed Chromium.
        if os.environ.get("T2S_CHROMIUM_PATH"):
            launch_options["executable_path"] = os.environ["T2S_CHROMIUM_PATH"]
        try:
            browser = pw.chromium.launch(**launch_options)
        except Exception as exc:
            pytest.skip(
                f"Chromium unavailable: {exc}. Run: python -m playwright install chromium"
            )
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture
def browser_page(chromium, seeded_deck, project_root: Path):
    client, db, deck_id = seeded_deck
    sid = start_study(client, deck_id)
    css = (project_root / "app/static/css/app.css").read_text(encoding="utf-8")
    js = (project_root / "app/static/js/study.js").read_text(encoding="utf-8")
    app_js = (project_root / "app/static/js/app.js").read_text(encoding="utf-8")
    pages = []

    def build(width=390, theme="light"):
        page = chromium.new_page(viewport={"width": width, "height": 850})
        pages.append(page)
        fresh_html = client.get(f"/study/{sid}").text
        soup = BeautifulSoup(fresh_html, "html.parser")
        for element in soup.select('script[src],link[rel="stylesheet"]'):
            element.decompose()
        page.set_content(str(soup))
        page.add_style_tag(content=css)
        page.evaluate("""(theme) => {
            document.documentElement.dataset.theme = theme;
            window.__speech = [];
            window.__cancelled = 0;
            Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{
                getVoices:()=>[{lang:'de-DE',localService:true},{lang:'en-GB',localService:true}],
                addEventListener:()=>{},
                cancel:()=>window.__cancelled++,
                speak:(u)=>window.__speech.push({text:u.text,lang:u.lang,rate:u.rate})
            }});
            window.SpeechSynthesisUtterance = function(text){this.text = text;};
        }""", theme)

        def bridge(body):
            response = client.post(
                f"/study/{sid}/settings", content=body,
                headers={"Accept": "application/json",
                         "Content-Type": "application/x-www-form-urlencoded"},
            )
            return {"status": response.status_code, "body": response.json()}

        page.expose_function("__saveSettings", bridge)
        page.evaluate("""() => {
            window.__forceSaveFailure = false;
            window.__requests = [];
            window.fetch = async (_url, options) => {
                window.__requests.push(options.body.toString());
                if (window.__forceSaveFailure) {
                    return {ok:false,status:503,json:async()=>({detail:'Offline'})};
                }
                const result = await window.__saveSettings(options.body.toString());
                return {ok:result.status<300,status:result.status,
                        json:async()=>result.body};
            };
        }""")
        page.add_script_tag(content=js)
        page.add_script_tag(content=app_js)
        return page

    yield build, db, sid
    for page in pages:
        page.close()


@pytest.mark.parametrize("width", [320, 390, 768, 1024, 1440])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_settings_popover_and_layout(browser_page, width, theme):
    build, _db, _sid = browser_page
    page = build(width, theme)
    assert page.locator("#answer").is_hidden()
    assert page.locator("#rating-actions").is_hidden()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator("#settings-trigger").click()
    assert page.locator("#study-settings").is_visible()
    bounds = page.locator("#study-settings").bounding_box()
    assert bounds is not None and 0 <= bounds["x"] <= width
    assert bounds["x"] + bounds["width"] <= width + 1
    page.keyboard.press("Escape")
    assert page.locator("#study-settings").is_hidden()
    assert page.evaluate("document.activeElement.id") == "settings-trigger"


def test_settings_saved_and_restored_by_server(browser_page):
    build, db, sid = browser_page
    page = build()
    page.locator("#settings-trigger").click()
    page.locator("#auto-speak").select_option("front_back")
    page.wait_for_function("document.querySelector('#settings-save-status').textContent === 'Saved'")
    page.locator("#speech-rate").fill("1.8")
    page.locator("#speech-rate").blur()
    page.wait_for_function("document.querySelector('#settings-save-status').textContent === 'Saved'")
    assert db.get_study_session_state(sid)["auto_speak"] == "front_back"
    assert db.get_study_session_state(sid)["speech_rate"] == 1.8
    # Re-rendering via the real server is separately asserted in the route tests.


def test_keyboard_reveal_and_audio(browser_page):
    build, db, sid = browser_page
    page = build()
    page.locator("#speak-front").click()
    assert page.evaluate("window.__speech.at(-1).lang") == "de-DE"
    page.locator(".study-eyebrow").click()
    page.keyboard.press("r")
    assert page.evaluate("window.__speech.length") == 2
    page.keyboard.press("Space")
    assert page.locator("#answer").is_visible()
    assert page.locator("#rating-actions").is_visible()
    page.evaluate("""() => {
        document.querySelector('#rating-actions').addEventListener('submit', e => {
            e.preventDefault();
            window.__submittedRating = new FormData(e.target, e.submitter).get('rating');
        });
    }""")
    page.keyboard.press("2")
    page.wait_for_function("window.__submittedRating === 'good'")
    assert page.evaluate("window.__cancelled") >= 1


def test_settings_failure_retry(browser_page):
    build, db, sid = browser_page
    page = build()
    old = db.get_study_session_state(sid)["auto_speak"]
    page.locator("#settings-trigger").click()
    page.evaluate("window.__forceSaveFailure=true")
    page.locator("#auto-speak").select_option("front")
    page.wait_for_function(
        "document.querySelector('#settings-save-status').dataset.state === 'error'"
    )
    assert db.get_study_session_state(sid)["auto_speak"] == old
    page.evaluate("window.__forceSaveFailure=false")
    page.locator("#settings-retry").click()
    page.wait_for_function("document.querySelector('#settings-save-status').textContent === 'Saved'")
    assert db.get_study_session_state(sid)["auto_speak"] == "front"


def test_rapid_setting_changes_latest_wins(browser_page):
    build, db, sid = browser_page
    page = build()
    page.locator("#settings-trigger").click()
    page.evaluate("""() => {
        const oldFetch = window.fetch;
        let count = 0;
        window.fetch = async (...args) => {
            count += 1;
            if (count === 1) await new Promise(resolve => setTimeout(resolve, 500));
            return oldFetch(...args);
        };
    }""")
    for value in ("front", "front_back", "off"):
        page.locator("#auto-speak").select_option(value)
    page.wait_for_function(
        "document.querySelector('#settings-save-status').textContent === 'Saved'",
        timeout=8000,
    )
    assert db.get_study_session_state(sid)["auto_speak"] == "off"
    assert page.evaluate("window.__requests.length") >= 2


def test_missing_speech_voices_is_non_blocking(browser_page):
    build, _db, _sid = browser_page
    page = build()
    page.evaluate("""() => {
        Object.defineProperty(window, 'speechSynthesis', {configurable:true,value:{
            getVoices:()=>[], addEventListener:()=>{}, cancel:()=>{}, speak:()=>{}
        }});
    }""")
    page.locator("#speak-front").click()
    assert "voices" in page.locator("#audio-status").inner_text().lower()
    page.locator(".study-eyebrow").click()
    page.keyboard.press("Space")
    assert page.locator("#answer").is_visible()


def test_auto_reveal_follows_saved_delay(browser_page):
    build, _db, _sid = browser_page
    page = build()
    page.locator("#settings-trigger").click()
    page.locator("#auto-reveal").check()
    page.locator("#reveal-delay").fill("1")
    page.locator("#reveal-delay").blur()
    page.wait_for_function("document.querySelector('#settings-save-status').textContent === 'Saved'")
    page.keyboard.press("Escape")
    page.locator("#answer").wait_for(state="visible", timeout=3500)


def test_fresh_render_uses_saved_autospeak(browser_page):
    build, db, sid = browser_page
    # Mimic the user's next page render with settings persisted in SQLite.
    db.update_study_session_settings(
        sid, auto_reveal=False, reveal_delay_seconds=5,
        auto_speak="front_back", speech_rate=1.4,
    )
    page = build()
    page.wait_for_function("window.__speech.length > 0")
    assert page.evaluate("window.__speech[0].lang") == "de-DE"
    assert page.evaluate("window.__speech.length") == 1
    page.locator(".study-eyebrow").click()
    page.keyboard.press("Space")
    assert page.evaluate("window.__speech.at(-1).lang") == "en-GB"
    assert page.evaluate("window.__speech.at(-1).rate") == 1.4
