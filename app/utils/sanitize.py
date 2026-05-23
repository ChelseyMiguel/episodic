"""
HTML sanitization utilities using bleach.

All user-generated text content (article body, bio, submission body, notes, etc.)
must be passed through sanitize_html() before storage and/or rendering.

Allowed tags are deliberately minimal — only basic formatting that makes sense
for a literary magazine. No scripts, iframes, forms, or event handlers.
"""
import bleach

# Tags allowed in rich text fields (article body, bio, submission body)
ALLOWED_TAGS: list[str] = [
    "p", "br", "strong", "em", "u", "s",
    "h2", "h3", "h4",
    "ul", "ol", "li",
    "blockquote", "a",
    "hr",
]

# Tags allowed in plain text fields (notes, author notes, descriptions)
PLAIN_TEXT_TAGS: list[str] = []

ALLOWED_ATTRIBUTES: dict[str, list[str]] = {
    "a": ["href", "title", "rel"],
}


def sanitize_html(text: str | None) -> str | None:
    """
    Sanitize rich text content. Strips all disallowed tags and attributes.
    Safe for storage in body/bio fields.
    """
    if text is None:
        return None
    return bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )


def sanitize_plain(text: str | None) -> str | None:
    """
    Strip all HTML from plain text fields (e.g. author notes, bios, editorial notes).
    Returns plain text with no markup.
    """
    if text is None:
        return None
    return bleach.clean(text, tags=PLAIN_TEXT_TAGS, attributes={}, strip=True)
