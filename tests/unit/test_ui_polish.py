"""Brand contrast and UI polish regression checks."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _luminance(color: str) -> float:
    values = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in values]
    return sum(channel * weight for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def _contrast(first: str, second: str) -> float:
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def test_text_contrast_is_safe_on_brand_surfaces() -> None:
    # Pink is an accent surface; use blue text on it. White text is reserved for blue.
    assert _contrast("#09318D", "#FD91CC") >= 4.5
    assert _contrast("#FFFFFF", "#09318D") >= 4.5


def test_styles_cover_hover_focus_responsive_and_reduced_motion() -> None:
    css = (ROOT / "src" / "quillseek" / "ui" / "styles.css").read_text(encoding="utf-8")
    assert ":hover" in css
    assert "focus-visible" in css
    assert "@media (max-width: 640px)" in css
    assert "prefers-reduced-motion: reduce" in css
    assert "--qs-blue: #09318D" in css and "--qs-pink: #FD91CC" in css


def test_launcher_supplies_brand_favicon() -> None:
    launcher = (ROOT / "scripts" / "run_frontend.py").read_text(encoding="utf-8")
    assert "favicon_path=" in launcher
    assert (ROOT / "assets" / "favicon.svg").is_file()


def test_manual_ui_checklist_tracks_unavailable_browser_automation() -> None:
    checklist = (ROOT / "docs" / "UI_MANUAL_CHECKLIST.md").read_text(encoding="utf-8")
    assert "developer console" in checklist
    assert "Screenshots requested for Step 10.2" in checklist
