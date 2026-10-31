"""Brand asset and design token checks for Step 8.1."""

from pathlib import Path
import xml.etree.ElementTree as ET

from quillseek.ui.theme import ACCENT, PRIMARY, THEME, WHITE

ROOT = Path(__file__).resolve().parents[2]
SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"
BRAND_COLORS = {"#09318D", "#FFFFFF", "#FD91CC"}


def test_brand_color_constants_match_the_plan() -> None:
    assert PRIMARY == "#09318D"
    assert WHITE == "#FFFFFF"
    assert ACCENT == "#FD91CC"


def test_logo_and_favicon_are_valid_svg_using_only_brand_colors() -> None:
    assets = ROOT / "assets"
    for filename in ("logo.svg", "logo-dark.svg", "favicon.svg"):
        root = ET.parse(assets / filename).getroot()
        assert root.tag == f"{SVG_NAMESPACE}svg"
        assert root.attrib["viewBox"]
        used_colors = set()
        for element in root.iter():
            for attribute in ("fill", "stroke"):
                value = element.attrib.get(attribute)
                if value and value != "none":
                    used_colors.add(value.upper())
        assert used_colors <= BRAND_COLORS
        assert used_colors


def test_custom_theme_imports_and_css_is_available() -> None:
    import gradio as gr

    assert isinstance(THEME, gr.themes.Base)
    stylesheet = ROOT / "src" / "quillseek" / "ui" / "styles.css"
    css = stylesheet.read_text(encoding="utf-8")
    assert "--qs-blue: #09318D" in css
    assert "--qs-pink: #FD91CC" in css
    assert "@media (max-width: 640px)" in css
