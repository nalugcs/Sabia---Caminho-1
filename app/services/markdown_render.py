from __future__ import annotations

import bleach
import markdown as markdown_lib

ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "ul",
    "ol",
    "li",
    "h2",
    "h3",
    "h4",
    "blockquote",
    "code",
    "pre",
]


def render_markdown(text: str) -> str:
    """Converte Markdown do LLM em HTML seguro (sem scripts/atributos)."""

    html = markdown_lib.markdown(text or "", extensions=["extra", "sane_lists"])
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes={}, strip=True)
