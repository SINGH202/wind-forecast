"""Product constants shared by services and routes."""

from datetime import date

# Decisions made in January cover delivery day D when D-1 is in January.
SCOPE_START = date(2026, 1, 2)
SCOPE_END = date(2026, 2, 1)
CUTOFF_OPTIONS = ("08:00", "08:30", "09:00")
HORIZON_LABEL = "All forecast vintages, grouped by horizon"
HORIZON_EDGES = (0, 6, 12, 24, 48)
MIN_HORIZON_HOURS = 0
MAX_HORIZON_HOURS = 48
ASSUMPTIONS = (
    "Delivery days run from 2 January to 1 February 2026.",
    "The decision forecast is the latest publish at or before the cutoff on D-1.",
    "The default cutoff is 09:00 Europe/London. Allowed cutoffs are 08:00 to 09:00.",
    "Explorer is a horizon view and does not use the decision cutoff.",
    "Error is forecast minus actual. A positive error is an over-forecast.",
    "Firm wind uses decision-forecast errors from delivery days before the selected day.",
    "There is no demand series, so residual demand is not computed.",
)
