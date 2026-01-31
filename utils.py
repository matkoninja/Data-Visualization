import textwrap
import pandas as pd


def wrap_text(text, width=15):
    """Wrap text to specified width, breaking on spaces when possible"""
    if pd.isna(text) or not isinstance(text, str):
        return str(text)
    # Use HTML line breaks for Plotly
    return '<br>'.join(textwrap.wrap(text, width=width))


def rgba(hex_color, alpha=0.4):
    hex_color = hex_color.lstrip("#")
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"

class Colors:
    SECONDARY = "#747478"
    PRIMARY = "#FF1E00"
    BLACK = "#0C0A00"
    BG_PANEL = "#F2F0EF"