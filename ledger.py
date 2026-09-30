"""UI-independent operations on the ledger: create, edit, delete, undo, search, month view.

Widgets call these; none of them know about Qt. Every method either returns the
record state the UI should show or raises ``ValueError`` (user input) /
``DatabaseError`` (storage) without leaving partial state behind.

Records handed to the UI carry the category to *show*: the person's own if they stated one
(``category_by_user``), otherwise the software's current judgement (classification.py),
which is derived here on every read and never written back.
"""
from dataclasses import dataclass
from datetime import datetime
from classification import Classifier
from database import Database
from domain import CATEGORIES, group_by_day, summarize_records, parse_stored_datetime, validate_record

UNSET = object()
AUTO = object()  # remove an explicit label; future reads use local learning again


@dataclass(frozen=True)
class MonthView:
    year: int
    month: int
    records: list
    totals: dict
    groups: list  # [(day, [records])]

    @property
    def is_empty(self):
        return not self.records


class Ledger:
    def __init__(self, database: Database):
        self.database = database
        self._classifier = None  # built from the person's labels on first use

    # ---- interpretation ----------------------------------------------
    def classifier(self):
        if self._classifier is None:
            self._classifier = Classifier(self.database.user_labels())
        return self._classifier

    def reload(self):
        """Forget what was learnt in memory; the next read rebuilds it from the stored labels."""
        self._classifier = None

    def interpret(self, stored):
        """The record as Review shows it: the person's category, else the derived one."""
        record = dict(stored)
        by_user = bool(record.get("category_by_user"))
        record["category_by_user"] = by_user
        if not by_user:
            record["category"] = self.classifier().classify(record["description"])
        return record

    def _learn(self, stored):
        """Keep the in-memory labels equal to the stored ones after a write."""
        if self._classifier is None:
            return
        if stored["category_by_user"]:
            self._classifier.set_label(stored["id"], stored["description"], stored["category"],
                                       (stored["updated_at"], stored["id"]))
        else:
            self._classifier.drop_label(stored["id"])

    # ---- Capture -----------------------------------------------------
    def create(self, amount_cents, when, description=""):
        """Store the facts only; the category is derived whenever the record is read."""
        description = description.strip()
        validate_record(amount_cents, when, None, description)
        record_id = self.database.add_record(amount_cents, when, None, description)
        return self.interpret(self.database.get_record(record_id))

    def undo_create(self, record_id):
        self.database.delete_record(record_id)
        if self._classifier is not None:
            self._classifier.drop_label(record_id)

    # ---- Review ------------------------------------------------------
    def month(self, year, month):
        self.reload()  # derived from the stored labels as they are now (~2 ms per 1,000 labels)
        records = [self.interpret(r) for r in self.database.get_records_by_month(year, month)]
        return MonthView(year, month, records, summarize_records(records), group_by_day(records))

    def search(self, text):
        self.reload()
        return [self.interpret(r) for r in self.database.search_records(text)]

    def update(self, record, *, amount_cents=UNSET, when=UNSET, category=UNSET, description=UNSET):
        """Apply the given field changes to ``record`` and return the fresh record.
        Giving a category (including None, 暂未判断) makes it the person's own."""
        stored = self.database.get_record(record["id"])
        new_amount = stored["amount_cents"] if amount_cents is UNSET else amount_cents
        new_when = parse_stored_datetime(stored["datetime"]) if when is UNSET else when
        new_description = stored["description"] if description is UNSET else description.strip()
        if category is AUTO:
            new_category, by_user = None, False
        elif category is UNSET:
            new_category, by_user = stored["category"], stored["category_by_user"]
        else:
            new_category, by_user = category, True
        self.database.update_record(record["id"], new_amount, new_when, new_category, new_description,
                                    category_by_user=by_user)
        fresh = self.database.get_record(record["id"])
        self._learn(fresh)
        return self.interpret(fresh)

    def update_undoable(self, record, **changes):
        """Return the display record and raw snapshots, never derived training labels."""
        before = self.database.get_record(record["id"])
        fresh = self.update(record, **changes)
        after = self.database.get_record(record["id"])
        return fresh, (before, after)

    def undo_update(self, receipt):
        before, after = receipt
        self.database.revert_update(before, after)
        self.reload()
        return self.interpret(before)

    def delete(self, record):
        """Delete and hand back the stored snapshot needed to restore it."""
        snapshot = self.database.get_record(record["id"])
        self.database.delete_record(record["id"])
        if self._classifier is not None:
            self._classifier.drop_label(record["id"])
        return snapshot

    def restore(self, snapshot):
        self.database.restore_record(snapshot)
        stored = self.database.get_record(snapshot["id"])
        self._learn(stored)
        return self.interpret(stored)

    def backup_to(self, destination):
        return self.database.backup_to(destination)

    @staticmethod
    def categories():
        return CATEGORIES

    @staticmethod
    def now():
        return datetime.now().replace(second=0, microsecond=0)
