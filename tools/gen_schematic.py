#!/usr/bin/env python3
"""Generate the KiCad 7 schematic (hardware/sht45_breakout.kicad_sch).

Every pin gets a short wire stub that ends in a net label or power symbol, so
connectivity is explicit and easy to review. Symbols are embedded from the
stock KiCad libraries.
"""
import math
import os
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "hardware", "sht45_breakout.kicad_sch")
SYMDIR = "/usr/share/kicad/symbols"
PROJECT = "sht45_breakout"

# Fixed UUIDs so the PCB can reference the schematic symbols (and so the
# output is reproducible run to run).
NS = uuid.UUID("6f1e2b1c-45a0-4c1e-9a55-5ab7e0b5c0de")


def uid(name):
    return str(uuid.uuid5(NS, name))


ROOT_UUID = uid("root-sheet")


def lib_symbol(lib, name):
    s = open(os.path.join(SYMDIR, lib + ".kicad_sym")).read()
    i = s.find('(symbol "%s"' % name)
    assert i >= 0, (lib, name)
    d = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            d += 1
        elif s[j] == ")":
            d -= 1
            if d == 0:
                break
    body = s[i:j + 1]
    # Top-level symbol gets the "Lib:Name" id; sub units keep the short name.
    return body.replace('(symbol "%s"' % name, '(symbol "%s:%s"' % (lib, name), 1)


# Pin tables in library coordinates (y up): number -> (x, y, angle)
PINS = {
    "Sensor_Humidity:SHT4x": {"1": (-7.62, -2.54, 0), "2": (-7.62, 2.54, 0),
                              "3": (2.54, 7.62, 270), "4": (2.54, -7.62, 90)},
    "power:PWR_FLAG": {"1": (0, 0, 90)},
    "Mechanical:MountingHole": {},
    "Device:R": {"1": (0, 3.81, 270), "2": (0, -3.81, 90)},
    "Device:C": {"1": (0, 3.81, 270), "2": (0, -3.81, 90)},
    "Jumper:SolderJumper_2_Bridged": {"1": (-3.81, 0, 0), "2": (3.81, 0, 180)},
    "Connector_Generic:Conn_01x04": {"1": (-5.08, 2.54, 0), "2": (-5.08, 0, 0),
                                     "3": (-5.08, -2.54, 0), "4": (-5.08, -5.08, 0)},
}

items = []
pwr_count = [0]


def fmt(v):
    return ("%.4f" % v).rstrip("0").rstrip(".")


def eff(size=1.27, hide=False, justify=None):
    j = " (justify %s)" % justify if justify else ""
    h = " hide" if hide else ""
    return "(effects (font (size %s %s))%s%s)" % (fmt(size), fmt(size), j, h)


def prop(name, value, x, y, hide=False, justify=None, idx=None):
    return '    (property "%s" "%s" (at %s %s 0) %s)\n' % (
        name, value, fmt(x), fmt(y), eff(hide=hide, justify=justify))


def symbol(lib_id, ref, value, x, y, footprint="", datasheet="", fields=None,
           ref_at=None, val_at=None, in_bom=True, on_board=True, key=None, mirror=False):
    key = key or ref
    u = uid("sym-" + key)
    rx, ry = ref_at if ref_at else (x + 2.54, y - 1.27)
    vx, vy = val_at if val_at else (x + 2.54, y + 1.27)
    hide_ref = ref.startswith("#")
    m = " (mirror y)" if mirror else ""
    s = '  (symbol (lib_id "%s") (at %s %s 0)%s (unit 1)\n' % (lib_id, fmt(x), fmt(y), m)
    s += "    (in_bom %s) (on_board %s) (dnp no)\n" % ("yes" if in_bom else "no",
                                                    "yes" if on_board else "no")
    s += "    (uuid %s)\n" % u
    s += prop("Reference", ref, rx, ry, hide=hide_ref, justify="left")
    s += prop("Value", value, vx, vy, justify="left")
    s += prop("Footprint", footprint, x, y, hide=True)
    s += prop("Datasheet", datasheet, x, y, hide=True)
    for k, v in (fields or {}).items():
        s += prop(k, v, x, y, hide=True)
    pins = PINS.get(lib_id, {"1": (0, 0, 0)})
    for n in pins:
        s += '    (pin "%s" (uuid %s))\n' % (n, uid("pin-%s-%s" % (key, n)))
    s += '    (instances (project "%s" (path "/%s" (reference "%s") (unit 1))))\n' % (
        PROJECT, ROOT_UUID, ref)
    s += "  )\n"
    items.append(s)
    return u


def pin_end(lib_id, x, y, n, mirror=False):
    px, py, a = PINS[lib_id][n]
    if mirror:
        px, a = -px, 180 - a
    # screen coordinates: y down. Outward direction is opposite the pin angle.
    ox, oy = -math.cos(math.radians(a)), math.sin(math.radians(a))
    return x + px, y - py, round(ox), round(oy)


def wire(x1, y1, x2, y2):
    items.append("  (wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid %s))\n"
                 % (fmt(x1), fmt(y1), fmt(x2), fmt(y2), uid("w-%s-%s-%s-%s" % (x1, y1, x2, y2))))


def label(name, x, y, ox, oy):
    angle = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(ox, oy)]
    just = "left bottom" if angle in (0, 90) else "right bottom"
    items.append('  (label "%s" (at %s %s %d) (fields_autoplaced)\n    %s\n    (uuid %s))\n'
                 % (name, fmt(x), fmt(y), angle, eff(justify=just), uid("lbl-%s-%s-%s" % (name, x, y))))


def power(kind, x, y):
    pwr_count[0] += 1
    ref = "#PWR0%02d" % pwr_count[0]
    lib = "power:" + kind
    if kind == "GND":
        symbol(lib, ref, "GND", x, y, ref_at=(x, y + 6.35), val_at=(x - 1.8, y + 4.2), key=ref)
    else:
        symbol(lib, ref, kind, x, y, ref_at=(x, y - 6.35), val_at=(x - 1.5, y - 4.0), key=ref)


def pwr_flag(x, y, key, left=False):
    pwr_count[0] += 1
    ref = "#FLG0%02d" % pwr_count[0]
    symbol("power:PWR_FLAG", ref, "PWR_FLAG", x, y, key=ref,
           ref_at=(x, y - 3.81), val_at=((x - 10.16) if left else (x + 1.27), y - 2.54))


def connect(lib_id, x, y, n, net, stub=2.54, mirror=False):
    """Draw a stub from pin n outward and terminate it with a label/power symbol."""
    px, py, ox, oy = pin_end(lib_id, x, y, n, mirror)
    ex, ey = px + ox * stub, py + oy * stub
    wire(px, py, ex, ey)
    if net in ("VCC", "GND"):
        power(net, ex, ey)
    else:
        label(net, ex, ey, ox, oy)


def text(t, x, y, size=1.27):
    t = t.replace('"', '\\"').replace("\n", "\\n")
    items.append('  (text "%s" (at %s %s 0)\n    (effects (font (size %s %s)) (justify left top))\n    (uuid %s))\n'
                 % (t, fmt(x), fmt(y), fmt(size), fmt(size), uid("txt-" + t[:40])))


LCSC = "LCSC"
FP_SHT = "Sensor_Humidity:Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad"
DS_SHT = "https://sensirion.com/media/documents/33FD6951/6A7C10A0/HT_DS_Datasheet_SHT4x_V7.3.pdf"

# ---------------------------------------------------------------- header
HX, HY = 63.5, 88.9
CONN = "Connector_Generic:Conn_01x04"
symbol(CONN, "J1", "I2C", HX, HY,
       footprint="Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
       ref_at=(HX - 1.27, HY - 5.08), val_at=(HX - 1.27, HY + 8.89), mirror=True)
# pin 1 -> VCC (+ PWR_FLAG)
px, py, _, _ = pin_end(CONN, HX, HY, "1", True)
wire(px, py, px + 5.08, py)
wire(px + 5.08, py, px + 5.08, py - 2.54)
wire(px + 5.08, py - 2.54, px + 5.08, py - 5.08)
power("VCC", px + 5.08, py - 5.08)
pwr_flag(px + 5.08, py - 2.54, "vcc")
# pin 2 -> GND (+ PWR_FLAG), routed around the signal labels
px, py, _, _ = pin_end(CONN, HX, HY, "2", True)
wire(px, py, px + 15.24, py)
wire(px + 15.24, py, px + 15.24, py + 10.16)
wire(px + 15.24, py + 10.16, px + 15.24, py + 12.7)
power("GND", px + 15.24, py + 12.7)
pwr_flag(px + 15.24, py + 10.16, "gnd", left=True)
connect(CONN, HX, HY, "3", "SCL", mirror=True)
connect(CONN, HX, HY, "4", "SDA", mirror=True)

# J2: JST XH, same pin order as J1
XX, XY = 63.5, 66.04
symbol(CONN, "J2", "XH", XX, XY,
       footprint="Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
       ref_at=(XX - 1.27, XY - 5.08), val_at=(XX - 1.27, XY + 8.89), mirror=True)
px, py, _, _ = pin_end(CONN, XX, XY, "1", True)
wire(px, py, px + 5.08, py)
wire(px + 5.08, py, px + 5.08, py - 5.08)
power("VCC", px + 5.08, py - 5.08)
px, py, _, _ = pin_end(CONN, XX, XY, "2", True)
wire(px, py, px + 15.24, py)
wire(px + 15.24, py, px + 15.24, py + 12.7)
power("GND", px + 15.24, py + 12.7)
connect(CONN, XX, XY, "3", "SCL", mirror=True)
connect(CONN, XX, XY, "4", "SDA", mirror=True)

# ---------------------------------------------------------------- mounting holes
for i, x in enumerate((190.5, 203.2)):
    symbol("Mechanical:MountingHole", "H%d" % (i + 1), "M2", x, 63.5,
           footprint="MountingHole:MountingHole_2.2mm_M2", in_bom=False,
           ref_at=(x + 2.54, 62.23), val_at=(x + 2.54, 64.77))

# ---------------------------------------------------------------- pull-ups
for ref, x, net in (("R1", 101.6, "SDA"), ("R2", 111.76, "SCL")):
    y = 88.9
    symbol("Device:R", ref, "10k", x, y, footprint="Resistor_SMD:R_0603_1608Metric",
           fields={LCSC: "C25804", "Tolerance": "1%"},
           ref_at=(x + 2.54, y - 1.27), val_at=(x + 2.54, y + 1.27))
    connect("Device:R", x, y, "1", "PU")
    connect("Device:R", x, y, "2", net)

JX, JY = 106.68, 73.66
symbol("Jumper:SolderJumper_2_Bridged", "JP1", "PULLUP", JX, JY,
       footprint="Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm",
       ref_at=(JX - 2.54, JY - 3.81), val_at=(JX - 3.81, JY + 2.54), in_bom=False)
connect("Jumper:SolderJumper_2_Bridged", JX, JY, "1", "VCC")
connect("Jumper:SolderJumper_2_Bridged", JX, JY, "2", "PU")

# ---------------------------------------------------------------- sensor
UX, UY = 144.78, 88.9
symbol("Sensor_Humidity:SHT4x", "U1", "SHT45-AD1B-R2", UX, UY, footprint=FP_SHT, datasheet=DS_SHT,
       fields={LCSC: "C9900092421", "MPN": "SHT45-AD1B-R2", "Manufacturer": "Sensirion"},
       ref_at=(UX - 5.08, UY - 7.62), val_at=(UX - 5.08, UY + 7.62))
connect("Sensor_Humidity:SHT4x", UX, UY, "1", "SDA")
connect("Sensor_Humidity:SHT4x", UX, UY, "2", "SCL")
connect("Sensor_Humidity:SHT4x", UX, UY, "3", "VCC")
connect("Sensor_Humidity:SHT4x", UX, UY, "4", "GND")

# ---------------------------------------------------------------- decoupling
CX, CY = 167.64, 88.9
symbol("Device:C", "C1", "100nF", CX, CY, footprint="Capacitor_SMD:C_0603_1608Metric",
       fields={LCSC: "C14663", "Voltage": "50V", "Dielectric": "X7R"},
       ref_at=(CX + 2.54, CY - 1.27), val_at=(CX + 2.54, CY + 1.27))
connect("Device:C", CX, CY, "1", "VCC")
connect("Device:C", CX, CY, "2", "GND")

# ---------------------------------------------------------------- notes
text("SHT45 I2C breakout", 50.8, 50.8, size=2.54)
text("J1 (2.54 mm header) / J2 (JST XH 2.50 mm): 1=VCC  2=GND  3=SCL  4=SDA\n"
     "VCC = 1.08 ... 3.6 V  (NOT 5 V tolerant!)\n"
     "I2C address 0x44 (SHT45-AD1B), up to 1 MHz (Fm+)", 50.8, 114.3)
text("R1/R2: 10k pull-ups as in datasheet Fig.1 (Rp >= 390R @ VDD >= 1.62V).\n"
     "JP1 (bottom side) is bridged by default. Cut the trace between its pads\n"
     "to disconnect both pull-ups when the bus already has them.", 50.8, 127)
text("C1: 100nF placed directly at U1 VDD/VSS (datasheet Fig.1).\n"
     "U1: die pad NOT soldered and no copper under the sensor (datasheet 5.3).\n"
     "U1 sits on a narrow PCB tongue for thermal decoupling (Sensirion Design Guide ch.3).", 50.8, 139.7)

# ---------------------------------------------------------------- write
libs = [("Sensor_Humidity", "SHT4x"), ("Device", "R"), ("Device", "C"),
        ("Jumper", "SolderJumper_2_Bridged"), ("Connector_Generic", "Conn_01x04"),
        ("power", "VCC"), ("power", "GND"), ("power", "PWR_FLAG"),
        ("Mechanical", "MountingHole")]
out = "(kicad_sch (version 20230121) (generator eeschema)\n\n"
out += "  (uuid %s)\n\n" % ROOT_UUID
out += '  (paper "A4")\n\n'
out += ('  (title_block\n    (title "SHT45 Breakout")\n    (date "2026-09-29")\n    (rev "1.0")\n'
        '    (comment 1 "Sensirion SHT45 humidity & temperature sensor, I2C")\n'
        '    (comment 2 "Board 16.0 x 19.8 mm, 2 layers, 2x M2 holes")\n  )\n\n')
out += "  (lib_symbols\n"
for lib, name in libs:
    out += "    " + lib_symbol(lib, name).replace("\n", "\n    ") + "\n"
out += "  )\n\n"
out += "".join(items)
out += '\n  (sheet_instances\n    (path "/" (page "1"))\n  )\n)\n'
open(OUT, "w").write(out)
print("wrote", OUT)
