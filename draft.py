"""Unfinished Capture input kept between launches. Draft ≠ Record.

A draft is a small JSON file beside the ledger. It never enters the database,
so it cannot appear in Review, totals, search or the chart.
"""
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import logging
import os
import tempfile
from pathlib import Path

DRAFT_FILE = "draft.json"


@dataclass(frozen=True)
class Draft:
    amount_text: str = ""
    description: str = ""
    when: str = ""  # canonical local time or "" (auto = now)

    @property
    def is_empty(self):
        return not self.amount_text.strip() and not self.description.strip()

    def when_as_datetime(self):
        if not self.when:
            return None
        try:
            return datetime.strptime(self.when, "%Y-%m-%d %H:%M")
        except ValueError:
            return None


class DraftStore:
    def __init__(self, directory: Path):
        self.path = Path(directory) / DRAFT_FILE

    def load(self):
        """Return the stored draft or None; an unreadable file is ignored, never fatal."""
        try:
            payload = json.loads(self.path.read_text("utf-8"))
            draft = Draft(str(payload.get("amount_text", "")), str(payload.get("description", "")),
                          str(payload.get("when", "")))
        except (OSError, ValueError, TypeError, AttributeError):
            return None
        return None if draft.is_empty else draft

    def save(self, draft: Draft) -> bool:
        """Replace atomically so a failed write leaves the previous draft intact."""
        if draft.is_empty:
            return self.clear()
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix=".draft-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(asdict(draft), stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            return True
        except OSError:
            logging.warning("Could not persist Capture draft", exc_info=True)
            return False
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def clear(self) -> bool:
        try:
            self.path.unlink(missing_ok=True)
            return True
        except OSError:
            logging.warning("Could not clear Capture draft", exc_info=True)
            return False
