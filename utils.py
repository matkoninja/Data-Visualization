import textwrap
import pandas as pd


def wrap_text(text, width=15):
    """Wrap text to specified width, breaking on spaces when possible"""
    if pd.isna(text) or not isinstance(text, str):
        return str(text)
    # Use HTML line breaks for Plotly
    return '<br>'.join(textwrap.wrap(text, width=width))
