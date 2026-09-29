#!/usr/bin/env bash
# Regenerate schematic + PCB and all manufacturing outputs (KiCad 7 + kicad-cli).
set -euo pipefail
cd "$(dirname "$0")/.."

export KICAD7_FOOTPRINT_DIR=${KICAD7_FOOTPRINT_DIR:-/usr/share/kicad/footprints}
export KICAD7_SYMBOL_DIR=${KICAD7_SYMBOL_DIR:-/usr/share/kicad/symbols}

HW=hardware
PCB=$HW/sht45_breakout.kicad_pcb
SCH=$HW/sht45_breakout.kicad_sch
OUT=production
GBR=$OUT/gerbers

python3 tools/gen_schematic.py
python3 tools/gen_pcb.py > /dev/null
python3 tools/drc.py $HW/drc_report.txt | grep -E "Found"

rm -rf "$OUT" && mkdir -p "$GBR" docs

# Gerbers (Protel extensions, what JLCPCB/PCBWay expect) + Excellon drill
kicad-cli pcb export gerbers -o "$GBR/" --subtract-soldermask \
  --layers F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts "$PCB" > /dev/null
kicad-cli pcb export drill -o "$GBR/" --format excellon --excellon-units mm \
  --excellon-zeros-format decimal --excellon-separate-th \
  --generate-map --map-format gerberx2 "$PCB" > /dev/null
# drop the NPTH drill/map files when the board has no non-plated holes
if ! grep -q '^T[0-9]' "$GBR"/*-NPTH.drl; then rm -f "$GBR"/*-NPTH*; fi
(cd "$GBR" && zip -q -r ../sht45_breakout_gerbers.zip .)

# Assembly files (JLCPCB format BOM + CPL)
kicad-cli pcb export pos -o "$OUT/pos_raw.csv" --format csv --units mm --side front \
  --use-drill-file-origin "$PCB" > /dev/null
python3 tools/jlc_assembly.py "$OUT/pos_raw.csv" "$OUT"
rm "$OUT/pos_raw.csv"

# Documentation: schematic PDF, board PDFs and PNG previews
kicad-cli sch export pdf -o docs/sht45_breakout_schematic.pdf "$SCH" > /dev/null
kicad-cli pcb export pdf -o docs/pcb_top.pdf --include-border-title \
  --layers F.Cu,F.SilkS,F.Mask,Edge.Cuts "$PCB" > /dev/null
kicad-cli pcb export pdf -o docs/pcb_bottom.pdf --include-border-title --mirror \
  --layers B.Cu,B.SilkS,B.Mask,Edge.Cuts "$PCB" > /dev/null
python3 tools/render.py docs
# Independent check: render the actual Gerber files with gerbv (if installed)
if command -v gerbv > /dev/null; then
  G=$GBR/sht45_breakout
  gerbv -x png -D 2000 -a -b '#1a1a1a' -o docs/gerber_top.png \
    -f '#ffffffff' $G-Edge_Cuts.gm1 -f '#e8e8e8ff' $G-F_Silkscreen.gto -f '#d4a84aff' $G-F_Paste.gtp \
    -f '#1f6b2aa0' $G-F_Mask.gts -f '#b87333ff' $G-F_Cu.gtl 2> /dev/null
  gerbv -x png -D 2000 -a -b '#1a1a1a' -o docs/gerber_bottom.png \
    -f '#ffffffff' $G-Edge_Cuts.gm1 -f '#e8e8e8ff' $G-B_Silkscreen.gbo \
    -f '#1f6b2aa0' $G-B_Mask.gbs -f '#b87333ff' $G-B_Cu.gbl 2> /dev/null
fi
echo "done: $OUT/ docs/"
