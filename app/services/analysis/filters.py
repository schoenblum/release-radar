"""The analysis inclusion filter and the view filter (R8.4.1, phase-2 brief §5.1).

Both are the same shape: each dimension is either None (no restriction) or the set of values
allowed. The *analysed* filter decides what medians, spreads, ranks and every score's comparison
set are computed from (D14 as amended); the *shown* filter only picks which of those appear. The
writer is never a dimension (D9).
"""

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.analysis.dataset import Row

# Researcher gender as stored on the researcher; a release without one counts as not recorded.
GENDERS = ("F", "M", "other", "not_recorded")


@dataclass(frozen=True)
class AnalysisFilter:
    # A None inside a set stands for "none": releases without a type, unit or field.
    release_types: frozenset[uuid.UUID | None] | None = None
    academic_years: frozenset[int] | None = None
    units: frozenset[uuid.UUID | None] | None = None
    fields: frozenset[uuid.UUID | None] | None = None
    embargoed: frozenset[bool] | None = None
    genders: frozenset[str] | None = None

    def matches(self, row: "Row") -> bool:
        checks = (
            (self.release_types, row.release_type_id),
            (self.academic_years, row.academic_year),
            (self.units, row.unit_id),
            (self.fields, row.field_id),
            (self.embargoed, row.embargoed),
            (self.genders, row.gender),
        )
        return all(allowed is None or value in allowed for allowed, value in checks)


EVERYTHING = AnalysisFilter()
