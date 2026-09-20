"""UI-independent operations on the ledger: create, edit, delete, undo, search, month view.

Widgets call these; none of them know about Qt. Every method either returns the
record state the UI should show or raises ``ValueError`` (user input) /
``DatabaseError`` (storage) without leaving partial state behind.
"""
from dataclasses import dataclass
from datetime import datetime
from classification import derive_category
from database import Database
from domain import CATEGORIES, group_by_day, summarize_records, parse_stored_datetime, validate_record

UNSET = object()


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

    # ---- Capture -----------------------------------------------------
    def create(self, amount_cents, when, description=""):
        """Store the facts, derive the interpretation, return the stored record."""
        description = description.strip()
        validate_record(amount_cents, when, None, description)
        category = derive_category(description, self.database.latest_category_for)
        record_id = self.database.add_record(amount_cents, when, category, description)
        return self.database.get_record(record_id)

    def undo_create(self, record_id):
        self.database.delete_record(record_id)

    # ---- Review ------------------------------------------------------
    def month(self, year, month):
        records = self.database.get_records_by_month(year, month)
        return MonthView(year, month, records, summarize_records(records), group_by_day(records))

    def search(self, text):
        return self.database.search_records(text)

    def update(self, record, *, amount_cents=UNSET, when=UNSET, category=UNSET, description=UNSET):
        """Apply the given field changes to ``record`` and return the fresh stored record."""
        new_amount = record["amount_cents"] if amount_cents is UNSET else amount_cents
        new_when = parse_stored_datetime(record["datetime"]) if when is UNSET else when
        new_category = record["category"] if category is UNSET else category
        new_description = record["description"] if description is UNSET else description.strip()
        self.database.update_record(record["id"], new_amount, new_when, new_category, new_description)
        return self.database.get_record(record["id"])

    def delete(self, record):
        """Delete and hand back the snapshot needed to restore it."""
        snapshot = dict(record)
        self.database.delete_record(record["id"])
        return snapshot

    def restore(self, snapshot):
        self.database.restore_record(snapshot)
        return self.database.get_record(snapshot["id"])

    @staticmethod
    def categories():
        return CATEGORIES

    @staticmethod
    def now():
        return datetime.now().replace(second=0, microsecond=0)
