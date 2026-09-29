#!/usr/bin/env python3
"""Turn KiCad's position CSV into JLCPCB CPL + BOM files.

Usage: jlc_assembly.py pos_raw.csv OUTDIR
LCSC part numbers are read from the footprint "LCSC" property in the PCB.
"""
import csv
import os
import sys
from collections import OrderedDict

import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pos_csv, outdir = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(os.path.join(ROOT, "hardware", "sht45_breakout.kicad_pcb"))
info = {}
for fp in board.GetFootprints():
    props = fp.GetProperties()
    info[fp.GetReference()] = {
        "value": fp.GetValue(),
        "fp": str(fp.GetFPID().GetLibItemName()),
        "lcsc": props.get("LCSC", ""),
        "bom": not (fp.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_BOM),
        "pos": not (fp.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_POS_FILES),
    }

rows = list(csv.DictReader(open(pos_csv)))
with open(os.path.join(outdir, "sht45_breakout_cpl.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for r in rows:
        rot = float(r["Rot"]) % 360
        w.writerow([r["Ref"], "%.4fmm" % float(r["PosX"]), "%.4fmm" % float(r["PosY"]),
                    "Top" if r["Side"] == "top" else "Bottom", "%g" % rot])

groups = OrderedDict()
for ref in sorted(info):
    i = info[ref]
    if not (i["bom"] and i["pos"]) or not i["lcsc"]:
        continue  # header (hand soldered) and solder jumper are not assembled
    groups.setdefault((i["value"], i["fp"], i["lcsc"]), []).append(ref)
with open(os.path.join(outdir, "sht45_breakout_bom.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for (val, fpn, lcsc), refs in groups.items():
        w.writerow([val, ",".join(refs), fpn, lcsc])
print("BOM/CPL written to", outdir)
