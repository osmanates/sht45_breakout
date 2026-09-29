#!/usr/bin/env python3
"""Generate the KiCad 7 PCB (hardware/sht45_breakout.kicad_pcb) with pcbnew.

Board: 16.0 x 19.8 mm, 2 layers. The SHT45 sits on a 4.4 mm wide tongue that is
separated from the rest of the board by milled slots (Sensirion Design Guide,
ch. 3 / Fig. 8b), with only four thin traces crossing over. Two "ears" either
side of the tongue carry M2 mounting holes; a 2.54 mm pin header and a JST XH
connector share the same pin order at the bottom edge.

Coordinates are in mm, KiCad convention (y grows downwards). The board's
top-left corner is at (100, 100).
"""
import math
import os
import uuid

import pcbnew
from pcbnew import FromMM, VECTOR2I

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "hardware", "sht45_breakout.kicad_pcb")
FPLIB = "/usr/share/kicad/footprints"
NS = uuid.UUID("6f1e2b1c-45a0-4c1e-9a55-5ab7e0b5c0de")  # same as gen_schematic.py


def P(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


# ------------------------------------------------------------------ geometry
X0, Y0 = 100.0, 100.0
W, H = 16.0, 19.8
TONGUE_L, TONGUE_R = 105.8, 110.2  # 4.4 mm wide sensor tongue
SLOT_W = 1.2                        # milled slot between tongue and ears
BASE_TOP = 106.0                    # tongue/ears: y 100..106, base: y 106..119.8
R_CORNER = 0.5
HOLES = [(102.3, 102.6), (113.7, 102.6)]  # M2, centred in the ears

SX, SY = 107.6, 102.4               # U1 centre
HDR_Y = 111.1
HDR_X = [104.19, 106.73, 109.27, 111.81]  # J1 pins 1..4 (VCC GND SCL SDA)
XH_Y = 115.75
XH_X = [104.25, 106.75, 109.25, 111.75]   # J2 (JST XH, 2.50 mm) pins 1..4

W_TONGUE = 0.15                     # thin traces on the tongue (less heat flow)
W_SIG = 0.20
W_PWR = 0.25
VIA_D, VIA_DRILL = 0.6, 0.3

board = pcbnew.NewBoard(OUT)

# ------------------------------------------------------------------ settings
ds = board.GetDesignSettings()
ds.SetCopperLayerCount(2)
ds.SetBoardThickness(FromMM(1.6))
ds.m_MinClearance = FromMM(0.15)
ds.m_TrackMinWidth = FromMM(0.15)
ds.m_ViasMinSize = FromMM(0.5)
ds.m_ViasMinAnnularWidth = FromMM(0.13)
ds.m_MinThroughDrill = FromMM(0.3)
ds.m_HoleClearance = FromMM(0.25)
ds.m_HoleToHoleMin = FromMM(0.5)
ds.m_CopperEdgeClearance = FromMM(0.3)
ds.m_SilkClearance = FromMM(0.0)
ds.m_MinSilkTextHeight = FromMM(0.7)
ds.m_MinSilkTextThickness = FromMM(0.15)
nc = ds.m_NetSettings.m_DefaultNetClass
nc.SetClearance(FromMM(0.15))
nc.SetTrackWidth(FromMM(W_SIG))
nc.SetViaDiameter(FromMM(VIA_D))
nc.SetViaDrill(FromMM(VIA_DRILL))
ds.SetAuxOrigin(P(X0, Y0 + H))       # bottom-left corner: drill/placement origin
ds.SetGridOrigin(P(X0, Y0 + H))

tb = board.GetTitleBlock()
tb.SetTitle("SHT45 Breakout")
tb.SetRevision("1.0")
tb.SetDate("2026-09-29")
tb.SetComment(0, "16.0 x 19.8 mm, 2 layers, 1.6 mm FR4, HASL/ENIG")

# ------------------------------------------------------------------ nets
NETS = {}
for name in ("VCC", "GND", "/SDA", "/SCL", "/PU"):
    n = pcbnew.NETINFO_ITEM(board, name)
    board.Add(n)
    NETS[name] = n

# ------------------------------------------------------------------ outline


def edge_line(a, b):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(P(*a))
    s.SetEnd(P(*b))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(FromMM(0.05))
    board.Add(s)


def edge_arc(a, m, b):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetArcGeometry(P(*a), P(*m), P(*b))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(FromMM(0.05))
    board.Add(s)


def rounded_outline(pts, r):
    """Closed polygon of axis-aligned edges; every corner filleted with r."""
    n = len(pts)
    segs = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        d1 = ((p1[0] - p0[0]), (p1[1] - p0[1]))
        l1 = math.hypot(*d1)
        d1 = (d1[0] / l1, d1[1] / l1)
        d2 = ((p2[0] - p1[0]), (p2[1] - p1[1]))
        l2 = math.hypot(*d2)
        d2 = (d2[0] / l2, d2[1] / l2)
        t1 = (p1[0] - d1[0] * r, p1[1] - d1[1] * r)
        t2 = (p1[0] + d2[0] * r, p1[1] + d2[1] * r)
        c = (t1[0] + d2[0] * r, t1[1] + d2[1] * r)
        v = (p1[0] - c[0], p1[1] - c[1])
        lv = math.hypot(*v)
        m = (c[0] + v[0] / lv * r, c[1] + v[1] / lv * r)
        segs.append((t1, m, t2))
    for i in range(n):
        t1, m, t2 = segs[i]
        edge_arc(t1, m, t2)
        edge_line(t2, segs[(i + 1) % n][0])


rounded_outline([
    (X0, Y0), (TONGUE_L - SLOT_W, Y0), (TONGUE_L - SLOT_W, BASE_TOP), (TONGUE_L, BASE_TOP),
    (TONGUE_L, Y0), (TONGUE_R, Y0), (TONGUE_R, BASE_TOP), (TONGUE_R + SLOT_W, BASE_TOP),
    (TONGUE_R + SLOT_W, Y0), (X0 + W, Y0), (X0 + W, Y0 + H), (X0, Y0 + H),
], R_CORNER)

# ------------------------------------------------------------------ footprints


def sym_path(ref):
    return pcbnew.KIID_PATH("/" + str(uuid.uuid5(NS, "sym-" + ref)))


def place(lib, name, ref, value, x, y, rot, nets, props=None, bottom=False,
          hide_ref=True, attrs=0):
    fp = pcbnew.FootprintLoad(os.path.join(FPLIB, lib + ".pretty"), name)
    assert fp, name
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    fp.SetPath(sym_path(ref))
    board.Add(fp)
    fp.SetPosition(P(x, y))
    fp.SetOrientationDegrees(rot)
    if bottom:
        fp.Flip(P(x, y), False)
    fp.Reference().SetVisible(not hide_ref)
    for k, v in (props or {}).items():
        fp.SetProperty(k, v)
    if attrs:
        fp.SetAttributes(fp.GetAttributes() | attrs)
    for pad in fp.Pads():
        net = nets.get(pad.GetNumber())
        if net:
            pad.SetNet(NETS[net])
    return fp


def pad_xy(fp, num):
    for pad in fp.Pads():
        if pad.GetNumber() == num:
            p = pad.GetPosition()
            return round(pcbnew.ToMM(p.x), 4), round(pcbnew.ToMM(p.y), 4)
    raise KeyError(num)


U1 = place("Sensor_Humidity", "Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad",
           "U1", "SHT45-AD1B-R2", SX, SY, -90,
           {"1": "/SDA", "2": "/SCL", "3": "VCC", "4": "GND"},
           {"LCSC": "C9900092421", "MPN": "SHT45-AD1B-R2"})
C1 = place("Capacitor_SMD", "C_0603_1608Metric", "C1", "100nF", SX, SY + 2.0, 0,
           {"1": "VCC", "2": "GND"}, {"LCSC": "C14663"})
# Pull-ups stacked on the right, pad 1 (PU) facing the board edge
R2 = place("Resistor_SMD", "R_0603_1608Metric", "R2", "10k", 111.5, 106.8, 180,
           {"1": "/PU", "2": "/SCL"}, {"LCSC": "C25804"})
R1 = place("Resistor_SMD", "R_0603_1608Metric", "R1", "10k", 111.5, 108.45, 180,
           {"1": "/PU", "2": "/SDA"}, {"LCSC": "C25804"})
J1 = place("Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical", "J1", "I2C",
           HDR_X[0], HDR_Y, 90, {"1": "VCC", "2": "GND", "3": "/SCL", "4": "/SDA"},
           attrs=pcbnew.FP_EXCLUDE_FROM_POS_FILES)
J2 = place("Connector_JST", "JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical", "J2", "XH",
           XH_X[0], XH_Y, 0, {"1": "VCC", "2": "GND", "3": "/SCL", "4": "/SDA"},
           attrs=pcbnew.FP_EXCLUDE_FROM_POS_FILES)
MH = [place("MountingHole", "MountingHole_2.2mm_M2", "H%d" % (i + 1), "M2", x, y, 0, {},
            attrs=pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)
      for i, (x, y) in enumerate(HOLES)]
JP1 = place("Jumper", "SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm", "JP1", "PULLUP",
            104.5, 107.3, 0, {"1": "VCC", "2": "/PU"}, bottom=True,
            attrs=pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)

# Pin header silk outline would collide with the pin labels on such a small
# board; pin 1 is identified by its square pad and the labels.
for item in list(J1.GraphicalItems()):
    if item.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
        J1.Remove(item)
# The bridged jumper footprint draws its reference on silk; keep it hidden.
for fp in (JP1,):
    fp.Value().SetVisible(False)

# Sanity-check the pad geometry the routing below relies on.
EXPECT = {
    (U1, "1"): (SX + 0.4, SY - 0.7), (U1, "2"): (SX - 0.4, SY - 0.7),
    (U1, "3"): (SX - 0.4, SY + 0.7), (U1, "4"): (SX + 0.4, SY + 0.7),
    (J1, "1"): (HDR_X[0], HDR_Y), (J1, "4"): (HDR_X[3], HDR_Y),
    (J2, "1"): (XH_X[0], XH_Y), (J2, "4"): (XH_X[3], XH_Y),
}
for (fp, num), (ex, ey) in EXPECT.items():
    px, py = pad_xy(fp, num)
    assert abs(px - ex) < 1e-3 and abs(py - ey) < 1e-3, (fp.GetReference(), num, px, py, ex, ey)

# ------------------------------------------------------------------ routing


def track(pts, net, width, layer=pcbnew.F_Cu):
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(P(*a))
        t.SetEnd(P(*b))
        t.SetWidth(FromMM(width))
        t.SetLayer(layer)
        t.SetNet(NETS[net])
        board.Add(t)


def via(x, y, net):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(P(x, y))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetWidth(FromMM(VIA_D))
    v.SetDrill(FromMM(VIA_DRILL))
    v.SetNet(NETS[net])
    board.Add(v)


u_sda, u_scl, u_vdd, u_vss = (pad_xy(U1, n) for n in "1234")
c_vcc, c_gnd = pad_xy(C1, "1"), pad_xy(C1, "2")
r2_pu, r2_scl = pad_xy(R2, "1"), pad_xy(R2, "2")
r1_pu, r1_sda = pad_xy(R1, "1"), pad_xy(R1, "2")
jp_vcc, jp_pu = pad_xy(JP1, "1"), pad_xy(JP1, "2")
j_vcc, j_gnd, j_scl, j_sda = ((x, HDR_Y) for x in HDR_X)

X_SDA, X_SCL = 109.15, 109.65        # tongue lanes (right side of U1, clear of C1)
SDA_VIA = (108.9, 108.2)
Y_SDA_HOP, Y_SCL_HOP = SY - 1.2, SY - 1.7

# --- tongue (thin traces, nothing under the sensor body)
# VDD / VSS straight down into C1, then on towards the header
track([u_vdd, c_vcc], "VCC", W_TONGUE)
track([u_vss, c_gnd], "GND", W_TONGUE)
# SDA: up out of the pad, over to its lane, down
track([u_sda, (u_sda[0], Y_SDA_HOP + 0.2), (u_sda[0] + 0.2, Y_SDA_HOP),
       (X_SDA - 0.2, Y_SDA_HOP), (X_SDA, Y_SDA_HOP + 0.2), (X_SDA, BASE_TOP + 0.5)],
      "/SDA", W_TONGUE)
# SCL: up, over the top of U1 (outside SDA), down its lane to the header
track([u_scl, (u_scl[0], Y_SCL_HOP + 0.2), (u_scl[0] + 0.2, Y_SCL_HOP),
       (X_SCL - 0.2, Y_SCL_HOP), (X_SCL, Y_SCL_HOP + 0.2), (X_SCL, BASE_TOP + 0.5)],
      "/SCL", W_TONGUE)

# --- base
track([c_vcc, (c_vcc[0], BASE_TOP + 0.2)], "VCC", W_TONGUE)
track([c_gnd, (c_gnd[0], BASE_TOP + 0.2)], "GND", W_TONGUE)
track([(c_vcc[0], BASE_TOP + 0.2), (c_vcc[0], BASE_TOP + 0.6),
       (j_vcc[0], BASE_TOP + 0.6 + (c_vcc[0] - j_vcc[0])), j_vcc], "VCC", W_PWR)
track([(c_gnd[0], BASE_TOP + 0.2), (c_gnd[0], BASE_TOP + 1.0),
       (j_gnd[0], BASE_TOP + 1.0 + (c_gnd[0] - j_gnd[0])), j_gnd], "GND", W_PWR)
track([(X_SCL, BASE_TOP + 0.5), (X_SCL, r2_scl[1]), (X_SCL, 110.0), j_scl], "/SCL", W_SIG)
track([(X_SCL, r2_scl[1]), r2_scl], "/SCL", W_SIG)
# SDA hops to the bottom layer under SCL and joins the header pin + R1
track([(X_SDA, BASE_TOP + 0.5), (SDA_VIA[0], BASE_TOP + 0.75), SDA_VIA], "/SDA", W_SIG)
via(*SDA_VIA, "/SDA")
track([SDA_VIA, (j_sda[0], SDA_VIA[1] + (j_sda[0] - SDA_VIA[0])), j_sda],
      "/SDA", W_SIG, pcbnew.B_Cu)
track([r1_sda, (j_sda[0], r1_sda[1] + (j_sda[0] - r1_sda[0])), j_sda], "/SDA", W_SIG)
# pull-up common node, then through the bottom-side jumper to VCC
# (the via sits between the four resistor pads, under the resistor bodies' gap)
VPU = (111.5, 107.625)
via(*VPU, "/PU")
track([r2_pu, VPU, r1_pu], "/PU", W_SIG)
track([VPU, (VPU[0] - 0.95, 106.8), (jp_pu[0], 106.8), jp_pu], "/PU", W_SIG, pcbnew.B_Cu)
track([jp_vcc, (jp_vcc[0], 109.6), (j_vcc[0], 109.9), j_vcc], "VCC", W_PWR, pcbnew.B_Cu)
# JST XH directly below the pin header, same pin order
for hx, xx, net, w in zip(HDR_X, XH_X, ("VCC", "GND", "/SCL", "/SDA"),
                          (W_PWR, W_PWR, W_SIG, W_SIG)):
    track([(hx, HDR_Y), (xx, XH_Y)], net, w)

# ------------------------------------------------------------------ silkscreen


def text(s, x, y, layer, size=0.8, thick=0.15, rot=0, justify=None):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(P(x, y))
    t.SetLayer(layer)
    t.SetTextSize(P(size, size))
    t.SetTextThickness(FromMM(thick))
    t.SetTextAngleDegrees(rot)
    if layer in (pcbnew.B_SilkS, pcbnew.B_Fab):
        t.SetMirrored(True)
    board.Add(t)
    return t


LABELS = ["VCC", "GND", "SCL", "SDA"]
for x, lbl in zip(HDR_X, LABELS):
    text(lbl, x, 109.6, pcbnew.F_SilkS, size=0.7)
    text(lbl, x, 109.6, pcbnew.B_SilkS, size=0.7)
text("SHT45", 108.0, 102.8, pcbnew.B_SilkS, size=0.8, rot=90)
text("0x44", 109.3, 102.8, pcbnew.B_SilkS, size=0.7, rot=90)
text("1.1-3.6V", 106.7, 102.9, pcbnew.B_SilkS, size=0.7, rot=90)
text("PU", 106.75, 107.5, pcbnew.B_SilkS, size=0.7)

# ------------------------------------------------------------------ save
board.BuildConnectivity()
pcbnew.SaveBoard(OUT, board)
print("wrote", OUT)
for fp in board.GetFootprints():
    print(fp.GetReference(), [(p.GetNumber(), pad_xy(fp, p.GetNumber()), p.GetNetname())
                               for p in fp.Pads()])
