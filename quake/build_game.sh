#!/usr/bin/env bash
# Genera todos los datos del juego en build/game (se meten en la raiz del APK).
# Requiere: FTEQCC, y QBSP/VIS/LIGHT (ericw-tools) en el PATH o en ERIC_DIR.
set -euo pipefail
Q="$(cd "$(dirname "$0")" && pwd)"
G="${GAME_OUT:-$Q/../build/game}"
FTEQCC="${FTEQCC:?falta FTEQCC}"
ERIC="${ERIC_DIR:-}"
rm -rf "$G" && mkdir -p "$G/maps"

echo "== QuakeC"
( cd "$Q/mod" && "$FTEQCC" -srcfile ssqc.src && "$FTEQCC" -srcfile csqc.src )
cp "$Q/progs.dat" "$Q/csprogs.dat" "$G/"

echo "== Assets"
python3 -I "$Q/assets/gen_sounds.py" "$G"
python3 -I "$Q/assets/gen_textures.py" "$G"
python3 -I "$Q/assets/gen_models.py" "$G"
# sonidos reales (reemplazan a los sintetizados con el mismo nombre)
cp -r "$Q/assets/sfx/." "$G/sound/"

echo "== Mapa"
W="$(mktemp -d)"
python3 -I "$Q/assets/gen_map.py" "$W/zombies.map"
cp "$G/wad/zm.wad" "$W/"
( cd "$W"
  "${ERIC}qbsp" -wadpath "$W" zombies.map
  "${ERIC}vis" zombies.bsp
  "${ERIC}light" -extra4 zombies.bsp )
cp "$W/zombies.bsp" "$G/maps/"
rm -rf "$G/wad"

cp "$Q/default.fmf" "$Q/fte.cfg" "$Q/touch.cfg" "$G/"
echo "== Contenido del juego"; ( cd "$G" && find . -type f | sort | head -80; du -sh . )
