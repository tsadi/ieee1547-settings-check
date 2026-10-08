"""Validate an inverter's trip and volt-var settings against IEEE 1547-2018."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from . import profiles as P

VOLT_FUNCS = ["OV2", "OV1", "UV1", "UV2"]
FREQ_FUNCS = ["OF2", "OF1", "UF1", "UF2"]


@dataclass
class Finding:
    severity: str  # FAIL, WARN, INFO
    function: str
    message: str


def _norm_trip(raw: dict, nominal_v: Optional[float]) -> dict:
    out = {}
    for name, s in raw.items():
        name = name.upper()
        pickup = s.get("pickup")
        if pickup is None and "pickup_v" in s:
            if not nominal_v:
                raise ValueError(f"{name}: pickup_v given but nominal_voltage_v missing")
            pickup = float(s["pickup_v"]) / float(nominal_v)
        out[name] = {"pickup": None if pickup is None else float(pickup),
                     "time": None if s.get("time") is None else float(s["time"])}
    return out


def _in(value: float, rng: tuple, eps: float = 1e-9) -> bool:
    return rng[0] - eps <= value <= rng[1] + eps


def check_settings(settings: dict) -> list[Finding]:
    cat = str(settings.get("category", "")).upper()
    if cat not in P.VOLTAGE_TRIP:
        raise ValueError("settings must include category I, II or III")
    profile = settings.get("profile")
    trip = _norm_trip(settings.get("trip", {}), settings.get("nominal_voltage_v"))
    findings: list[Finding] = []

    tables = dict(P.VOLTAGE_TRIP[cat])
    tables.update(P.FREQUENCY_TRIP)

    # 1. presence and allowable ranges
    for fn in VOLT_FUNCS + FREQ_FUNCS:
        s = trip.get(fn)
        if not s or s["pickup"] is None or s["time"] is None:
            findings.append(Finding("FAIL", fn, "missing pickup or clearing time"))
            continue
        ref = tables[fn]
        unit = "pu" if fn in VOLT_FUNCS else "Hz"
        if not _in(s["pickup"], ref["pickup_range"]):
            findings.append(Finding("FAIL", fn, f"pickup {s['pickup']:g} {unit} outside allowable "
                                    f"{ref['pickup_range'][0]:g}-{ref['pickup_range'][1]:g} {unit} (Category {cat})"))
        if not _in(s["time"], ref["time_range"]):
            findings.append(Finding("FAIL", fn, f"clearing time {s['time']:g} s outside allowable "
                                    f"{ref['time_range'][0]:g}-{ref['time_range'][1]:g} s (Category {cat})"))

    # 2. ordering between stages
    def pair(a, b, rel_pickup, rel_time):
        sa, sb = trip.get(a), trip.get(b)
        if not sa or not sb or None in (sa["pickup"], sb["pickup"], sa["time"], sb["time"]):
            return
        if rel_pickup == ">=" and sa["pickup"] < sb["pickup"]:
            findings.append(Finding("FAIL", f"{a}/{b}", f"{a} pickup must be at or beyond {b} pickup"))
        if rel_pickup == "<=" and sa["pickup"] > sb["pickup"]:
            findings.append(Finding("FAIL", f"{a}/{b}", f"{a} pickup must be at or below {b} pickup"))
        if rel_time and sa["time"] > sb["time"]:
            findings.append(Finding("FAIL", f"{a}/{b}", f"{a} (more severe) must clear no slower than {b}"))

    pair("OV2", "OV1", ">=", True)
    pair("UV2", "UV1", "<=", True)
    pair("OF2", "OF1", ">=", True)
    pair("UF2", "UF1", "<=", True)

    # 3. trips that reach into the continuous-operation window
    vlo, vhi = P.CONTINUOUS_OPERATION["voltage"]
    flo, fhi = P.CONTINUOUS_OPERATION["frequency"]
    if trip.get("OF1", {}).get("pickup") is not None and trip["OF1"]["pickup"] < fhi:
        findings.append(Finding("WARN", "OF1", f"pickup {trip['OF1']['pickup']:g} Hz is inside the "
                                f"continuous-operation band ({flo:g}-{fhi:g} Hz); confirm the utility asked for it"))
    if trip.get("UF1", {}).get("pickup") is not None and trip["UF1"]["pickup"] > flo:
        findings.append(Finding("WARN", "UF1", f"pickup {trip['UF1']['pickup']:g} Hz is inside the "
                                f"continuous-operation band ({flo:g}-{fhi:g} Hz); confirm the utility asked for it"))

    # 4. deviation from the selected default profile
    if profile:
        ref = P.expected_defaults(profile)
        for fn, exp in ref.items():
            s = trip.get(fn)
            if not s or s["pickup"] is None or s["time"] is None:
                continue
            tol = 0.005 if fn in VOLT_FUNCS else 0.05
            if abs(s["pickup"] - exp["pickup"]) > tol or abs(s["time"] - exp["time"]) > max(0.01, 0.01 * exp["time"]):
                findings.append(Finding("WARN", fn, f"differs from {P.PROFILES[profile]['label']}: "
                                        f"{s['pickup']:g}/{s['time']:g}s vs {exp['pickup']:g}/{exp['time']:g}s"))

    # 5. volt-var curve sanity
    vv = settings.get("volt_var")
    if vv:
        pts = [(float(v), float(q)) for v, q in vv]
        vs = [p[0] for p in pts]
        qs = [p[1] for p in pts]
        if any(b <= a for a, b in zip(vs, vs[1:])):
            findings.append(Finding("FAIL", "volt-var", "voltage points must increase strictly"))
        if any(b > a for a, b in zip(qs, qs[1:])):
            findings.append(Finding("FAIL", "volt-var", "reactive power must not increase with voltage "
                                    "(inject at low voltage, absorb at high voltage)"))
        if qs[0] < 0 or qs[-1] > 0:
            findings.append(Finding("FAIL", "volt-var", "curve must inject at low voltage and absorb at high voltage"))
        if profile == "rule21" and pts != P.RULE21["volt_var"]:
            findings.append(Finding("WARN", "volt-var", f"differs from Rule 21 default curve {P.RULE21['volt_var']}"))

    if not any(f.severity == "FAIL" for f in findings):
        findings.append(Finding("INFO", "all", f"no range or ordering violations for Category {cat}"))
    return findings


def render_markdown(settings: dict, findings: list[Finding]) -> str:
    cat = str(settings.get("category")).upper()
    name = settings.get("name", "Inverter settings")
    lines = [f"# {name}", "", f"Category {cat}" + (f" · profile `{settings['profile']}`" if settings.get("profile") else ""), ""]
    lines += ["| Severity | Function | Finding |", "|---|---|---|"]
    order = {"FAIL": 0, "WARN": 1, "INFO": 2}
    for f in sorted(findings, key=lambda x: order[x.severity]):
        lines.append(f"| {f.severity} | {f.function} | {f.message} |")
    fails = sum(f.severity == "FAIL" for f in findings)
    warns = sum(f.severity == "WARN" for f in findings)
    lines += ["", f"Result: {fails} fail, {warns} warning.", "",
              "_Reference values transcribed from public reproductions of IEEE 1547-2018 and CA Rule 21. "
              "Confirm against the standard and the utility's source requirements document._"]
    return "\n".join(lines) + "\n"
