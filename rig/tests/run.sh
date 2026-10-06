#!/bin/zsh
# run.sh [unit|render swap|render ds4|rpc [model]|loop [model]] — test the film-rig extension without pi's screen (2026-09-23).
#   unit          load the extension against a stub of pi's API: commands, tools, /film on/off/status,
#                 director prompt appended once, state restored on resume, image warning, lifecycle choice.
#                 No GPU. Seconds.
#   render swap   REAL render of stories/projects/00-rig-smoke.txt (2 x 5 s, 480p, ~2 min) in the
#                 llama-swap lifecycle: load a model first (any pi -p on local/vision-500k), the tool must
#                 unload it, render, report with a contact sheet.
#   render ds4    the same with an engine started by the human's control panel: `cd ~/repos/ds4 &&
#                 ./model vision --yes` first; the tool must `model stop`, render, `model vision`.
#   rpc [model]   REAL headless pi (--mode rpc) on local/vision-500k by default: /film status, /film <brief>
#                 (the model answers as the director), /film off. Loads the model; unload it afterwards.
#   loop [model]  THE FULL LOOP from a normal headless pi session (extension discovery on, persisted session,
#                 local/vision-500k by default): /film with a brief pointing at the smoke project; the model itself
#                 calls render_and_wait, is unloaded, the render runs, it reloads and reviews the sheet. ~4 min.
# Both render modes need an idle GPU and remove nothing: park ~/Videos/vidgen/rig-smoke yourself
# afterwards (the tool refuses to render a finished film).
set -eu
here=${0:a:h}
T=$(mktemp -d -t rigtest.XXXXXX); mkdir -p $T/node_modules
ln -s "$(npm root -g)/@earendil-works/pi-coding-agent/node_modules/typebox" $T/node_modules/typebox
cp $here/../film-rig.ts $T/film-rig.ts; echo '{"type":"module"}' > $T/package.json
case ${1:-unit} in
  unit)   sed 's|from "../film-rig.ts"|from "./film-rig.ts"|' $here/unit.mts > $T/t.mts; export FILM_RIG_UNIT_TEST=1 ;;
  rpc)    exec python3 $here/rpc.py "${2:-local/vision-500k}" ;;
  loop)   exec python3 $here/loop.py "${2:-local/vision-500k}" ;;
  render) sed 's|from "../film-rig.ts"|from "./film-rig.ts"|' $here/render.mts > $T/t.mts; export LIFECYCLE=${2:-swap} ;;
  *) echo "usage: run.sh [unit|render swap|render ds4|rpc [model]|loop [model]]"; exit 2 ;;
esac
cd $T && node --experimental-strip-types --no-warnings t.mts
