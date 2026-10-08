"""Reference data: IEEE 1547-2018 trip settings and a CA Rule 21 default profile.

Values transcribed from public sources that reproduce the standard's tables:

* NERC, "BPS-Connected Inverter-Based Resource ... IEEE 1547-2018" guideline,
  Tables 2.2 (voltage) and 2.3 (frequency): defaults and ranges of
  allowable settings, including the IEEE 1547a-2020 amendment changes.
* MISO / Unitil / NRECA implementation guides (defaults, ride-through).
* LADWP technical requirements derived from CA Rule 21 (Rule 21 defaults
  and the default volt-var curve).

Check against your licensed copy of IEEE 1547-2018 and the utility's
current source requirements document before relying on a result.
"""

# Each trip function: default pickup, default clearing time (s),
# allowable pickup range (min, max), allowable clearing-time range (min, max).
# Voltage pickup is per-unit of nominal; frequency pickup is Hz (60 Hz systems).

VOLTAGE_TRIP = {
    "I": {
        "OV2": {"pickup": 1.20, "time": 0.16, "pickup_range": (1.20, 1.20), "time_range": (0.16, 0.16)},
        "OV1": {"pickup": 1.10, "time": 2.0, "pickup_range": (1.10, 1.20), "time_range": (1.0, 13.0)},
        "UV1": {"pickup": 0.70, "time": 2.0, "pickup_range": (0.0, 0.88), "time_range": (2.0, 21.0)},
        "UV2": {"pickup": 0.45, "time": 0.16, "pickup_range": (0.0, 0.50), "time_range": (0.16, 2.0)},
    },
    "II": {
        "OV2": {"pickup": 1.20, "time": 0.16, "pickup_range": (1.20, 1.20), "time_range": (0.16, 0.16)},
        "OV1": {"pickup": 1.10, "time": 2.0, "pickup_range": (1.10, 1.20), "time_range": (1.0, 13.0)},
        "UV1": {"pickup": 0.70, "time": 10.0, "pickup_range": (0.0, 0.88), "time_range": (2.0, 21.0)},
        "UV2": {"pickup": 0.45, "time": 0.16, "pickup_range": (0.0, 0.50), "time_range": (0.16, 2.0)},
    },
    "III": {
        "OV2": {"pickup": 1.20, "time": 0.16, "pickup_range": (1.20, 1.20), "time_range": (0.16, 0.16)},
        "OV1": {"pickup": 1.10, "time": 13.0, "pickup_range": (1.10, 1.20), "time_range": (1.0, 13.0)},
        "UV1": {"pickup": 0.88, "time": 21.0, "pickup_range": (0.0, 0.88), "time_range": (2.0, 50.0)},
        "UV2": {"pickup": 0.50, "time": 2.0, "pickup_range": (0.0, 0.50), "time_range": (0.16, 21.0)},
    },
}

FREQUENCY_TRIP = {
    "OF2": {"pickup": 62.0, "time": 0.16, "pickup_range": (61.8, 66.0), "time_range": (0.16, 1000.0)},
    "OF1": {"pickup": 61.2, "time": 300.0, "pickup_range": (61.0, 66.0), "time_range": (180.0, 1000.0)},
    "UF1": {"pickup": 58.5, "time": 300.0, "pickup_range": (50.0, 59.0), "time_range": (180.0, 1000.0)},
    "UF2": {"pickup": 56.5, "time": 0.16, "pickup_range": (50.0, 57.0), "time_range": (0.16, 1000.0)},
}

# Continuous-operation windows the trip settings must leave alone.
CONTINUOUS_OPERATION = {
    "voltage": (0.88, 1.10),
    "frequency": (58.8, 61.2),
}

# CA Rule 21 default profile (smart inverter, Category III ride-through).
RULE21 = {
    "voltage": {
        "OV2": {"pickup": 1.20, "time": 0.16},
        "OV1": {"pickup": 1.10, "time": 13.0},
        "UV1": {"pickup": 0.88, "time": 21.0},
        "UV2": {"pickup": 0.50, "time": 2.0},
    },
    "frequency": {
        "OF2": {"pickup": 62.0, "time": 0.16},
        "OF1": {"pickup": 61.2, "time": 300.0},
        "UF1": {"pickup": 58.5, "time": 300.0},
        "UF2": {"pickup": 56.5, "time": 0.16},
    },
    "volt_var": [  # (voltage %, reactive power % of rating; + inject, - absorb)
        (92.0, 30.0),
        (97.0, 0.0),
        (103.0, 0.0),
        (107.0, -30.0),
    ],
    "volt_var_response_s": 5.0,
}

PROFILES = {
    "cat1": {"category": "I", "label": "IEEE 1547-2018 Category I defaults"},
    "cat2": {"category": "II", "label": "IEEE 1547-2018 Category II defaults"},
    "cat3": {"category": "III", "label": "IEEE 1547-2018 Category III defaults"},
    "rule21": {"category": "III", "label": "CA Rule 21 defaults (Category III)"},
}


def expected_defaults(profile: str) -> dict:
    """Default trip settings for a named profile as {function: {pickup, time}}."""
    if profile not in PROFILES:
        raise KeyError(f"unknown profile {profile!r}; choose from {sorted(PROFILES)}")
    if profile == "rule21":
        out = dict(RULE21["voltage"])
        out.update(RULE21["frequency"])
        return out
    cat = PROFILES[profile]["category"]
    out = {k: {"pickup": v["pickup"], "time": v["time"]} for k, v in VOLTAGE_TRIP[cat].items()}
    out.update({k: {"pickup": v["pickup"], "time": v["time"]} for k, v in FREQUENCY_TRIP.items()})
    return out
