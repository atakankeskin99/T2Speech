"""Real browser flows served as static files at the GitHub Pages project subpath."""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import threading

from bs4 import BeautifulSoup
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("prepare_demo", ROOT / "scripts/prepare_demo.py")
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


@pytest.fixture(scope="module")
def artifact(tmp_path_factory):
    return packager.prepare(tmp_path_factory.mktemp("pages") / "T2Speech")


def test_artifact_contains_only_public_files_and_identical_shared_assets(artifact):
    files = {p.relative_to(artifact).as_posix() for p in artifact.rglob("*") if p.is_file()}
    assert files == set(packager.DEMO_FILES) | set(packager.SHARED_ASSETS) | {".nojekyll"}
    for target, source in packager.SHARED_ASSETS.items():
        assert (artifact / target).read_bytes() == (ROOT / source).read_bytes()
    for html in artifact.glob("*.html"):
        text = html.read_text(encoding="utf-8")
        assert "{{" not in text and "{%" not in text
        soup = BeautifulSoup(text, "html.parser")
        for element in soup.select("[src], [href], form[action]"):
            link = element.get("src") or element.get("href") or element.get("action")
            assert not link.startswith("/"), (html.name, link)
            if not link.startswith("https:"):
                assert (artifact / link.split("?")[0]).is_file(), (html.name, link)
        assert not soup.select('form[method="post"]')


def test_sample_data_is_small_and_has_unique_stable_identifiers(artifact):
    decks = json.loads((artifact / "data/sample-decks.json").read_text(encoding="utf-8"))
    assert 2 <= len(decks) <= 4
    assert len({deck["id"] for deck in decks}) == len(decks)
    for deck in decks:
        assert deck["name"] and deck["description"] and deck["front_language"] and deck["back_language"]
        assert 1 <= len(deck["cards"]) <= 8
        assert len({card["id"] for card in deck["cards"]}) == len(deck["cards"])
        assert all(card["front"] and card["back"] for card in deck["cards"])


def test_packager_rejects_unexpected_files(tmp_path):
    (tmp_path / "private.db").write_text("private")
    with pytest.raises(ValueError, match="unexpected files"):
        packager.prepare(tmp_path)
    assert (tmp_path / "private.db").read_text() == "private"


@pytest.fixture(scope="module")
def static_url(artifact):
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(artifact.parent)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/T2Speech/"
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.fixture(scope="module")
def chromium_demo():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as pw:
        options = {"headless": True}
        if os.environ.get("T2S_CHROMIUM_PATH"):
            options["executable_path"] = os.environ["T2S_CHROMIUM_PATH"]
        try:
            browser = pw.chromium.launch(**options)
        except Exception as error:
            pytest.skip(f"Chromium unavailable: {error}")
        yield browser
        browser.close()


@pytest.fixture
def demo_page(chromium_demo, static_url):
    page = chromium_demo.new_page(viewport={"width": 1440, "height": 950})
    errors, requests = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: requests.append((request.method, request.url)))
    page.add_init_script("""window.__speech = []; window.__cancelled = 0;
        window.__voiceMode = 'ok';
        Object.defineProperty(window, 'speechSynthesis', {configurable:true, value:{
            getVoices: () => window.__voiceMode === 'empty' ? [] : [
                {lang:'de-DE', localService:true}, {lang:'en-GB', localService:true},
                {lang:'tr-TR', localService:true}],
            cancel: () => window.__cancelled++,
            speak: u => { if(window.__voiceMode === 'throw') throw Error('audio failure');
                window.__speech.push({text:u.text, lang:u.lang, rate:u.rate}); }
        }});
        window.SpeechSynthesisUtterance = function(text){this.text=text;};""")
    yield page
    assert not errors, errors
    assert all(method == "GET" and url.startswith(static_url) for method, url in requests), requests
    page.close()


def go(page, url):
    response = page.goto(url)
    assert response.status == 200
    page.locator("#demo-loading").wait_for(state="hidden")


def start(page, base, reverse=False):
    go(page, base + "study_setup.html?deck=german-essentials")
    page.locator("#shuffle").uncheck()
    if reverse:
        page.locator("#reverse").check()
    page.locator("#start-session").click()
    page.wait_for_url("**/study.html?session=*")
    page.locator("#page-content").wait_for(state="visible")
    return page.url


def stored(page):
    return page.evaluate("DemoApp.state()")


def test_full_flow_queue_resume_settings_replacement_and_completion(demo_page, static_url):
    page = demo_page
    go(page, static_url)
    assert page.locator(".deck-row").count() == 3
    page.get_by_role("link", name="German essentials", exact=True).click()
    page.locator("#page-content").wait_for(state="visible")
    assert page.locator(".card-list-item").count() == 6
    original_url = start(page, static_url)
    sid = original_url.split("session=")[1]
    assert page.locator("#front-text").inner_text() == "Guten Morgen!"
    page.locator("#front-text").click()
    page.keyboard.press("2")
    assert page.locator("#good-count").inner_text() == "0"
    page.keyboard.press("Space")
    assert page.locator("#answer").is_visible()
    page.keyboard.press("1")
    assert stored(page)["sessions"][sid]["pending"] == ["de-thanks", "de-please", "de-station", "de-hello", "de-understand", "de-later"]
    assert page.locator("#good-count").inner_text() == "0"
    page.keyboard.press("Space")
    page.evaluate("""() => { const button=document.querySelector('[value="good"]'); button.click(); button.click(); }""")
    assert page.locator("#good-count").inner_text() == "1"
    page.locator("#settings-trigger").click()
    page.locator("#auto-speak").select_option("front_back")
    page.locator("#speech-rate").fill("1.8")
    page.locator("#auto-reveal").check()
    page.locator("#reveal-delay").fill("2")
    page.locator("#auto-reveal").uncheck()
    before = stored(page)["sessions"][sid]
    assert before["settings"]["speech_rate"] == 1.8
    page.locator("#settings-close").click()
    page.locator(".study-back-link").click()
    page.wait_for_url("**/deck.html?deck=*")
    page.get_by_role("link", name="Resume session", exact=True).click()
    page.wait_for_url(original_url)
    page.locator("#page-content").wait_for(state="visible")
    assert stored(page)["sessions"][sid] == before
    go(page, static_url + f"study_complete.html?session={sid}")
    assert page.locator("#page-content").is_hidden()
    assert "not been completed" in page.locator("#demo-status").inner_text()


def test_resume_and_settings_survive_reload_and_back_navigation(demo_page, static_url):
    page = demo_page
    url = start(page, static_url, reverse=True)
    sid = url.split("session=")[1]
    assert page.locator("#front-text").inner_text() == "Good morning!"
    page.locator("#settings-trigger").click()
    page.locator("#auto-speak").select_option("front_back")
    page.locator("#speech-rate").fill("1.8")
    page.locator("#auto-reveal").check()
    page.locator("#reveal-delay").fill("2")
    assert page.locator("#settings-save-status").inner_text() == "Saved in this tab"
    page.keyboard.press("Escape")
    assert page.evaluate("document.activeElement.id") == "settings-trigger"
    page.locator("#front-text").click()
    page.keyboard.press("Space")
    assert page.evaluate("window.__speech.at(-1)") == {"text": "Guten Morgen!", "lang": "de-DE", "rate": 1.8}
    page.keyboard.press("r")
    assert page.evaluate("window.__speech.length") == 2
    page.keyboard.press("1")
    assert page.evaluate("window.__cancelled") >= 1
    before = stored(page)["sessions"][sid]
    page.reload()
    page.locator("#page-content").wait_for(state="visible")
    assert stored(page)["sessions"][sid] == before
    page.locator("#front-text").click()
    page.keyboard.press("Escape")
    page.wait_for_url("**/deck.html?deck=*")
    page.get_by_role("link", name="Resume session", exact=True).click()
    page.wait_for_url(url)
    page.locator("#page-content").wait_for(state="visible")
    assert stored(page)["sessions"][sid] == before
    page.locator("#settings-trigger").click()
    assert page.locator("#speech-rate").input_value() == "1.8"
    assert page.locator("#auto-reveal").is_checked()


def test_confirmation_abandonment_and_real_completion(demo_page, static_url):
    page = demo_page
    old_url = start(page, static_url)
    old_id = old_url.split("session=")[1]
    page.locator("#reveal-button").click()
    page.get_by_role("button", name="Good", exact=False).click()
    go(page, static_url + "study_setup.html?deck=german-essentials")
    page.locator("#start-session").click()
    assert page.locator("#replace-panel").is_visible()
    assert stored(page)["sessions"][old_id]["status"] == "active"
    page.locator("#cancel-replace").click()
    assert page.locator("#replace-panel").is_hidden()
    page.locator("#start-session").click()
    page.locator("#confirm-replace").click()
    page.wait_for_url("**/study.html?session=*")
    page.locator("#page-content").wait_for(state="visible")
    new_url = page.url
    assert stored(page)["sessions"][old_id]["status"] == "abandoned"
    go(page, static_url + f"study_complete.html?session={old_id}")
    assert page.locator("#page-content").is_hidden()
    assert "abandoned" in page.locator("#demo-status").inner_text()
    go(page, old_url)
    assert "abandoned" in page.locator("#demo-status").inner_text()
    go(page, new_url)
    for _ in range(6):
        page.locator("#reveal-button").click()
        page.get_by_role("button", name="Good", exact=False).click()
    page.wait_for_url("**/study_complete.html?session=*")
    page.locator("#page-content").wait_for(state="visible")
    assert page.locator("#completed-count").inner_text() == "6"
    page.get_by_role("link", name="Study again", exact=True).click()
    assert page.locator("#replace-panel").is_hidden()


def test_auto_reveal_cancel_invalid_settings_and_audio_failure(demo_page, static_url):
    page = demo_page
    start(page, static_url)
    page.locator("#settings-trigger").click()
    page.locator("#auto-reveal").check()
    page.locator("#reveal-delay").fill("1")
    page.locator("#speech-rate").fill("11")
    assert "between" in page.locator("#settings-save-status").inner_text()
    session = next(iter(stored(page)["sessions"].values()))
    assert session["settings"]["speech_rate"] == 1
    page.locator("#speech-rate").fill("10")
    page.locator("#settings-close").click()
    page.locator("#answer").wait_for(state="visible")
    page.get_by_role("button", name="Good", exact=False).click()
    page.locator("#settings-trigger").click()
    page.locator("#auto-reveal").uncheck()
    page.locator("#settings-close").click()
    page.wait_for_timeout(1150)
    assert page.locator("#answer").is_hidden()
    page.evaluate("window.__voiceMode='throw'")
    page.locator("#speak-front").click()
    assert "failed" in page.locator("#audio-status").inner_text()
    page.evaluate("window.__voiceMode='empty'")
    page.locator("#speak-front").click()
    assert "voices" in page.locator("#audio-status").inner_text()
    page.evaluate("Object.defineProperty(window,'speechSynthesis',{value:undefined})")
    page.locator("#speak-front").click()
    assert "unavailable" in page.locator("#audio-status").inner_text()
    page.locator("#reveal-button").click()
    page.get_by_role("button", name="Good", exact=False).click()
    assert page.locator("#good-count").inner_text() == "2"


@pytest.mark.parametrize("width", [320, 390, 768, 1024, 1440])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_all_pages_themes_and_mobile_layouts(demo_page, static_url, width, theme):
    page = demo_page
    page.set_viewport_size({"width": width, "height": 950})
    go(page, static_url)
    page.locator("#theme-select").select_option(theme)
    for path in ["deck.html?deck=german-essentials", "study_setup.html?deck=german-essentials"]:
        go(page, static_url + path)
        assert page.locator("#page-content").is_visible()
        assert page.evaluate("document.documentElement.dataset.theme") == theme
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        if os.environ.get("T2S_DEMO_SCREENSHOTS") and width in [390, 1440]:
            folder = Path(os.environ["T2S_DEMO_SCREENSHOTS"])
            folder.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(folder / f"{path.split('.')[0]}-{theme}-{width}.png"), full_page=True)
    page.locator("#start-session").click()
    page.wait_for_url("**/study.html?session=*")
    page.locator("#page-content").wait_for(state="visible")
    assert page.evaluate("document.documentElement.dataset.theme") == theme
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator("#settings-trigger").click()
    bounds = page.locator("#study-settings").bounding_box()
    assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width + 1
    if os.environ.get("T2S_DEMO_SCREENSHOTS") and width in [390, 1440]:
        page.screenshot(path=str(Path(os.environ["T2S_DEMO_SCREENSHOTS"]) / f"study-{theme}-{width}.png"), full_page=True)
    page.keyboard.press("Escape")
    for _ in range(6):
        page.locator("#reveal-button").click()
        page.get_by_role("button", name="Good", exact=False).click()
    page.wait_for_url("**/study_complete.html?session=*")
    page.locator("#page-content").wait_for(state="visible")
    assert page.evaluate("document.documentElement.dataset.theme") == theme
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    if os.environ.get("T2S_DEMO_SCREENSHOTS") and width in [390, 1440]:
        page.screenshot(path=str(Path(os.environ["T2S_DEMO_SCREENSHOTS"]) / f"complete-{theme}-{width}.png"), full_page=True)


def test_direct_missing_session_and_storage_recovery(demo_page, static_url):
    page = demo_page
    go(page, static_url + "study.html?session=missing")
    assert page.locator("#recovery").is_visible()
    go(page, static_url)
    page.evaluate("sessionStorage.setItem(DemoStorage.KEY, '{broken')")
    page.reload()
    page.locator("#recovery").wait_for(state="visible")
    page.on("dialog", lambda dialog: dialog.accept())
    page.locator("#reset-demo").click()
    page.wait_for_url("**/index.html")
    page.locator("#page-content").wait_for(state="visible")
    assert stored(page) == {"version": 1, "sessions": {}}


def test_failed_storage_write_does_not_commit_progress(demo_page, static_url):
    page = demo_page
    start(page, static_url)
    page.locator("#reveal-button").click()
    before = stored(page)
    page.evaluate("() => {window.__originalSave=DemoStorage.save; DemoStorage.save=()=>{throw Error('quota')}}")
    page.get_by_role("button", name="Good", exact=False).click()
    assert stored(page) == before
    assert page.locator("#good-count").inner_text() == "0"
    assert page.locator("#answer").is_visible()
    assert "browser tab storage" in page.locator("#demo-status").inner_text()
    page.evaluate("() => {DemoStorage.save=window.__originalSave}")
    page.get_by_role("button", name="Good", exact=False).click()
    assert page.locator("#good-count").inner_text() == "1"
