"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import profiles
from .check import check_settings, render_markdown


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ieee1547-check",
                                 description="Validate inverter trip / volt-var settings against IEEE 1547-2018")
    ap.add_argument("settings", type=Path, nargs="?", help="settings JSON file")
    ap.add_argument("-o", "--out", type=Path, help="write the markdown report here")
    ap.add_argument("--show-profile", choices=sorted(profiles.PROFILES), help="print a default profile and exit")
    args = ap.parse_args(argv)

    if args.show_profile:
        print(json.dumps(profiles.expected_defaults(args.show_profile), indent=2))
        return 0
    if not args.settings:
        ap.error("settings file is required")
    try:
        settings = json.loads(args.settings.read_text())
        findings = check_settings(settings)
    except (ValueError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    report = render_markdown(settings, findings)
    if args.out:
        args.out.write_text(report)
    print(report)
    return 1 if any(f.severity == "FAIL" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
