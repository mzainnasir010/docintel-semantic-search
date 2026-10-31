"""Quillseek Gradio theme and immutable brand color tokens."""

import gradio as gr

PRIMARY = "#09318D"
WHITE = "#FFFFFF"
ACCENT = "#FD91CC"

_BLUE = gr.themes.colors.Color(
    c50="#EEF2FC",
    c100="#D9E1F7",
    c200="#B4C4EF",
    c300="#8AA4E3",
    c400="#5E7FD0",
    c500="#315AB8",
    c600="#19439F",
    c700=PRIMARY,
    c800="#07266D",
    c900="#051D54",
    c950="#031238",
    name="quillseek-blue",
)
_PINK = gr.themes.colors.Color(
    c50="#FFF4FA",
    c100="#FFE5F3",
    c200="#FFC9E7",
    c300=ACCENT,
    c400="#F66DB8",
    c500="#E84B9F",
    c600="#C93280",
    c700="#A32265",
    c800="#741948",
    c900="#4B102F",
    c950="#2C091B",
    name="quillseek-pink",
)


def build_theme() -> gr.themes.Base:
    """Return the app theme, retaining readable blue/white contrast."""
    return (
        gr.themes.Base(
            primary_hue=_BLUE,
            secondary_hue=_PINK,
            neutral_hue=gr.themes.colors.slate,
            radius_size="lg",
            spacing_size="md",
            text_size="md",
        )
        .set(
            body_background_fill=WHITE,
            body_text_color=PRIMARY,
            body_text_color_subdued="#42577F",
            background_fill_primary=WHITE,
            background_fill_secondary="#F4F6FC",
            border_color_primary="#D9E1F7",
            button_primary_background_fill=PRIMARY,
            button_primary_background_fill_hover="#07266D",
            button_primary_text_color=WHITE,
            block_title_text_color=PRIMARY,
            block_label_text_color=PRIMARY,
            input_border_color_focus=ACCENT,
            checkbox_label_background_fill_selected=ACCENT,
        )
    )


THEME = build_theme()
