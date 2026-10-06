#!/bin/zsh
# film-pi.sh — start pi as the film director on a LOCAL model (2026-09-23).
#
#   rig/film-pi.sh [-m vision-q4-400k|vision-500k|qwen27-262k] [--resident] [--thinking L] [pi flags...] ["initial prompt"]
#
#   -m MODEL     llama-swap target (default vision-q4-400k = DeepSeek V4 Flash Vision, Q2/Q4 mix, the weights of
#                the 2026-09-24 film, then the 100K row vision-q4, removed 2026-10-02; vision-500k = the
#                IQ2XXS build; qwen27-262k for the co-resident experiment). The pi
#                catalog is generated: ~/repos/local-rig/tools/gen-pi-models.py
#   --resident   FILM_RIG_MODE=resident: keep the model loaded across renders (only qwen27-262k; ~35 GB as the old 131K qwen27,
#                fits beside a 480p render; DeepSeek does not). Default: alternate (unload before
#                each render, reload on the next reply).
#   --thinking L pi thinking level (default medium; DeepSeek renders low/medium/high alike).
#   -c / --session ID etc. pass through to pi. Works with the internet off (--offline is passed).
#
# Everything the director needs is local: the film-rig extension (rig/film-rig.ts, loaded
# explicitly with -e, extension discovery off so nothing else can call the model or the GPU),
# the film skill (~/.pi/agent/skills/film), and the system prompt rig/film-director.md (its
# frontmatter is for the subagent extension; only the body is appended here). --approve trusts this
# repo's .pi/settings.json for the run (compaction reserve 8192, keep 16000: without trust pi ignores it and
# compacted a 100K ds4 context at about 67K on 2026-09-24).
set -eu
here=${0:a:h}
model=vision-q4-400k; think=medium; export FILM_RIG_MODE=${FILM_RIG_MODE:-alternate}
args=()
while [ $# -gt 0 ]; do
  case $1 in
    -m) model=$2; shift 2;;
    --resident) export FILM_RIG_MODE=resident; shift;;
    --thinking) think=$2; shift 2;;
    *) args+=("$1"); shift;;
  esac
done
prompt=$(mktemp -t film-director.XXXXXX)
awk 'BEGIN{fm=0} NR==1 && /^---$/ {fm=1; next} fm==1 && /^---$/ {fm=2; next} fm!=1 {print}' $here/film-director.md > $prompt
cd ~/repos/local-video
# Self-heal the pi catalog (2026-09-23 20:40): `./ds4-serve <target>` (the human's `model` alias) rewrites
# ~/.pi/agent/models.json to a single `ds4` provider on :8000, and pi then cannot find local/$model.
# The rig runs on llama-swap (:8090) with the catalog from local-rig's generator; regenerate it when needed.
if ! pi --list-models 2>/dev/null | grep -Eq "^local +$model( |$)"; then
  echo "film-pi: pi catalog lacks local/$model (ds4-serve rewrote it); regenerating with gen-pi-models.py" >&2
  ~/repos/local-rig/tools/gen-pi-models.py >&2 || { echo "film-pi: generator failed; see ~/repos/local-rig/README.md" >&2; exit 1; }
fi
# A model server outside llama-swap (e.g. started by `model` / ds4-serve on :8000) keeps ~90 GB wired and
# the render tools will refuse. Say so now rather than after the interview.
if pgrep -x ds4-server >/dev/null && ! curl -s -m 2 127.0.0.1:8090/running | grep -q ds4; then
  echo "film-pi: a ds4-server is running outside llama-swap (pid $(pgrep -x ds4-server | head -1)); the rig cannot render beside it." >&2
  echo "         Stop it first: kill -TERM $(pgrep -x ds4-server | head -1)   (never -9)" >&2
  exit 1
fi
# Memory other apps hold (2026-09-26): a leaking visionOS simulator host with a 100 GB footprint left 4% free and
# stalled the orchestrator's first request for 6 min. The model needs about 93 GB; say so before the interview.
free=$(sysctl -n kern.memorystatus_level 2>/dev/null || echo 100)
if [ "$free" -lt 75 ] && ! curl -s -m 2 127.0.0.1:8090/running | grep -q '"model"'; then
  echo "film-pi: only ${free}% of memory is free with no model loaded; the orchestrator needs about 93 GB. Largest processes:" >&2
  top -l 1 -o mem -n 5 -stats pid,command,mem 2>/dev/null | tail -6 >&2
fi
# --no-context-files (2026-09-27): the repo now has a CLAUDE.md for Claude Code; pi would load it into the
# director's system prompt. The director's inputs stay film-director.md, the skills and the tools.
# The Mac's GPU hold (2026-10-04, ~/repos/local-rig/docs/hold.md): hold.ts makes this session's model calls wait while
# any GPU job (a render, m3d, the human's `hold on`) holds the GPU; it never calls the model itself. This launcher
# appends the director prompt without /film, so FILM_RIG_DIRECTOR=1 tells film-rig.ts this is the director.
export FILM_RIG_DIRECTOR=1
holdext=(); [ -f ~/repos/local-rig/extensions/hold.ts ] && holdext=(-e ~/repos/local-rig/extensions/hold.ts)
exec pi --offline --approve --no-extensions --no-context-files -e $here/film-rig.ts "${holdext[@]}" \
  --model local/$model --thinking $think \
  --append-system-prompt $prompt \
  --tools read,write,edit,ls,grep,find,bash,render_and_wait,review_scenes,redo_scenes,keep_take \
  "${args[@]}"
