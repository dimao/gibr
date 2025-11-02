"""Data class for issue representation."""

from dataclasses import dataclass

from slugify import slugify

from gibr.translate import auto_translate_if_needed


@dataclass
class Issue:
    """Simple representation of an issue from any tracker."""

    id: int
    title: str
    assignee: str
    type: str = "issue"
    translate: bool = True

    @property
    def sanitized_title(self) -> str:
        """Sanitized title with automatic translation if enabled."""
        title = self.title
        if self.translate:
            title = auto_translate_if_needed(title)
        return slugify(title)
