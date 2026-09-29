#!/usr/bin/env python3
"""Run KiCad DRC on the generated board and print the report summary."""
import os, sys
import pcbnew
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pcb = os.path.join(ROOT, "hardware", "sht45_breakout.kicad_pcb")
rpt = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "hardware", "drc_report.txt")
b = pcbnew.LoadBoard(pcb)
pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
print(open(rpt).read())
