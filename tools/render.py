#!/usr/bin/env python3
"""Render top/bottom PNG previews of the board (via kicad-cli PDF + pdftoppm)."""
import os
import subprocess
import sys
import tempfile

import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, "hardware", "sht45_breakout.kicad_pcb")
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs")
DPI, MARGIN, PAGE_W = 1200, 1.0, 297.0  # A4 landscape page used by the plotter

bb = pcbnew.LoadBoard(PCB).GetBoardEdgesBoundingBox()
x0, y0 = pcbnew.ToMM(bb.GetX()) - MARGIN, pcbnew.ToMM(bb.GetY()) - MARGIN
w, h = pcbnew.ToMM(bb.GetWidth()) + 2 * MARGIN, pcbnew.ToMM(bb.GetHeight()) + 2 * MARGIN
px = DPI / 25.4

views = {
    "top": ("F.Cu,F.Paste,F.SilkS,F.Mask,Edge.Cuts", False),
    "bottom": ("B.Cu,B.SilkS,B.Mask,Edge.Cuts", True),
}
with tempfile.TemporaryDirectory() as tmp:
    for name, (layers, mirror) in views.items():
        pdf = os.path.join(tmp, name + ".pdf")
        cmd = ["kicad-cli", "pcb", "export", "pdf", "-o", pdf, "--layers", layers, PCB]
        if mirror:
            cmd.insert(4, "--mirror")
        subprocess.run(cmd, check=True, capture_output=True)
        left = (PAGE_W - x0 - w) if mirror else x0
        subprocess.run(["pdftoppm", "-r", str(DPI), "-x", str(int(left * px)), "-y", str(int(y0 * px)),
                        "-W", str(int(w * px)), "-H", str(int(h * px)), "-png", "-singlefile",
                        pdf, os.path.join(out, "pcb_%s" % name)], check=True)
        print("rendered", os.path.join(out, "pcb_%s.png" % name))
