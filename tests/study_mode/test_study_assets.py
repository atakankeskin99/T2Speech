"""Cross-platform Study Mode asset and approved-theme regression checks."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import jinja2
import pytest


@pytest.mark.parametrize("asset", ["study.js", "app.js"])
def test_javascript_syntax(project_root: Path, asset: str):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed; JavaScript syntax not checked")
    path = project_root / "app" / "static" / "js" / asset
    subprocess.run([node, "--check", str(path)], check=True, capture_output=True)


@pytest.mark.parametrize("template", [
    "study.html", "study_setup.html", "study_complete.html", "deck.html",
])
def test_study_templates_parse(project_root: Path, template: str):
    source = (project_root / "app" / "templates" / template).read_text(encoding="utf-8")
    jinja2.Environment().parse(source)


def test_stylesheet_parses(project_root: Path):
    tinycss2 = pytest.importorskip("tinycss2")
    css = (project_root / "app" / "static" / "css" / "app.css").read_text(encoding="utf-8")
    errors = [token for token in tinycss2.parse_stylesheet(
        css, skip_whitespace=True, skip_comments=True,
    ) if token.type == "error"]
    assert not errors, errors


def test_approved_theme_tokens(project_root: Path):
    baseline_path = project_root / "tests" / "baseline_theme_tokens.json"
    assert baseline_path.is_file(), (
        "Place the approved baseline_theme_tokens.json at tests/baseline_theme_tokens.json"
    )
    expected = json.loads(baseline_path.read_text(encoding="utf-8"))
    css = (project_root / "app" / "static" / "css" / "app.css").read_text(encoding="utf-8")
    actual = {}
    for theme, selector in (
        ("light", ":root {"), ("dark", ':root[data-theme="dark"] {'),
    ):
        assert selector in css, f"Missing theme selector: {selector}"
        start = css.index(selector) + len(selector)
        block = css[start:css.index("}", start)]
        actual[theme] = dict(re.findall(r"(--color-[\w-]+)\s*:\s*([^;]+);", block))
    assert actual == expected, "Approved theme colors changed unexpectedly"


def test_settings_markup_has_matching_dom_hooks(project_root: Path):
    """Check contracts, without requiring a hard-coded ?v= cache-busting tag."""
    from bs4 import BeautifulSoup
    html = (project_root / "app" / "templates" / "study.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    for element_id in (
        "settings-trigger", "study-settings", "settings-close", "study-settings-form",
        "settings-save-status", "settings-retry", "auto-speak", "speech-rate",
        "auto-reveal", "reveal-delay", "reveal-button", "answer", "rating-actions",
    ):
        assert soup.find(id=element_id) is not None, f"Missing Study Mode hook: {element_id}"
    assert soup.select_one('script[src^="/static/js/study.js"]') is not None
