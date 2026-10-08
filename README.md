# ieee1547-settings-check

Checks an inverter's grid trip settings and volt-var curve against IEEE 1547-2018 (with the 1547a-2020 amendment) and the CA Rule 21 default profile.

Commissioning sheets, utility source-requirement documents and the inverter's own settings export rarely agree on the first try. This tool reads the settings you actually applied and tells you which ones are outside the standard's allowable range for the category, which stages are inconsistent with each other, which trips reach into the continuous-operation band, and where you differ from the default profile you were told to use.

## What it checks

| Check | Result if wrong |
|---|---|
| Every voltage (OV2, OV1, UV1, UV2) and frequency (OF2, OF1, UF1, UF2) stage is present | FAIL |
| Pickup and clearing time inside the allowable range for Category I, II or III | FAIL |
| Stage ordering: the more severe stage has the wider pickup and clears no slower | FAIL |
| OF1 / UF1 pickup inside the 58.8–61.2 Hz continuous-operation band | WARN |
| Difference from the selected default profile (`cat1`, `cat2`, `cat3`, `rule21`) | WARN |
| Volt-var curve: voltages increase, reactive power injects low / absorbs high | FAIL |
| Volt-var curve differs from the Rule 21 default (92/97/103/107 %, ±30 %) | WARN |

Exit code is 1 if any check fails, so it can gate a commissioning script or CI job.

## Example

```
pip install -e .
ieee1547-check examples/site_settings_480v.json
```

```
# 480 V BESS inverter, as-commissioned settings

Category III · profile `rule21`

| Severity | Function | Finding |
|---|---|---|
| WARN | UV2 | differs from CA Rule 21 defaults (Category III): 0.5/3s vs 0.5/2s |
| INFO | all | no range or ordering violations for Category III |

Result: 0 fail, 1 warning.
```

Print a default profile:

```
ieee1547-check --show-profile cat2
```

## Settings file

```json
{
  "name": "480 V BESS inverter",
  "category": "III",
  "profile": "rule21",
  "nominal_voltage_v": 480,
  "trip": {
    "OV2": {"pickup": 1.20, "time": 0.16},
    "UV1": {"pickup_v": 422.4, "time": 21.0},
    "OF1": {"pickup": 61.2, "time": 300}
  },
  "volt_var": [[92, 30], [97, 0], [103, 0], [107, -30]]
}
```

Voltage pickups can be per-unit (`pickup`) or volts (`pickup_v`, with `nominal_voltage_v`). Frequency is in Hz for 60 Hz systems.

## Reference data

All reference values live in `ieee1547_check/profiles.py` with their sources. They are transcribed from public documents that reproduce the standard's tables (NERC's IEEE 1547-2018 guideline, MISO / Unitil / NRECA implementation guides, and LADWP's Rule 21 technical requirements), not from the standard itself. Confirm against your licensed copy of IEEE 1547-2018 and the utility's current source requirements document before you sign anything.

Not covered yet: voltage and frequency ride-through durations, frequency-droop parameters, volt-watt, enter-service, and 50 Hz systems.

## Tests

```
pip install pytest
pytest
```

## License

MIT. Built by [Tsadi Shvo](https://www.linkedin.com/in/tsadishvo/), product safety and compliance for robotics, EV/BESS and power electronics.
