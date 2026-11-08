"""Monotonic printed folios across one source volume."""

import posixpath


def page_number_minimum(value=1):
    try:
        return max(1, min(10000, int(value)))
    except (TypeError, ValueError, OverflowError):
        return 1


def page_number_chapter(path):
    return posixpath.dirname(str(path).replace("\\", "/"))


class PageNumberSequence:
    def __init__(self, minimums=None):
        self.minimums = {
            str(chapter): page_number_minimum(value)
            for chapter, value in (minimums.items() if isinstance(minimums, dict) else [])
        }

    def minimum(self, chapter):
        # Chapters and TOC bookmarks divide the story, not the printed page
        # numbering. Keep their keys for resumable scan batches, but carry the
        # highest confirmed folio across every chapter of this source. A new
        # volume gets a new sequence instance and starts at one again.
        return max(self.minimums.values(), default=1)

    def observe(self, chapter, decision):
        if not decision.get("has_page_number"):
            return
        numbers = [int(text) for text in decision.get("recognizedDigits", {}).values()
                   if str(text).isascii() and str(text).isdecimal()]
        if numbers:
            self.minimums[str(chapter)] = max(self.minimum(chapter), max(numbers) + 1)
