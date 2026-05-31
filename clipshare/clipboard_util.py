"""
Cross-platform clipboard read/write via pyperclip.
"""

import pyperclip


def copy(text: str) -> None:
    """Copy text to the system clipboard."""
    pyperclip.copy(text)


def paste() -> str:
    """Return current text clipboard contents. Returns empty string when clipboard is empty or contains non-text."""
    try:
        result = pyperclip.paste()
        return result if isinstance(result, str) else ""
    except Exception:
        return ""
