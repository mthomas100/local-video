#!/bin/zsh
# follow-pi.sh view|history|events — watch the live pi director without touching it (2026-09-27, for the human).
#   view    pi's screen, live: the newest pi tmux session (plant<N> test runs, film<N> films) copied every second, and
#           the next one when it ends. It is not a tmux client, so keys cannot reach pi. Stop: Ctrl-C.
#   history a scrollable copy of the newest pi session's whole screen history in less (arrows/PgUp, / to search, q
#           refreshes it; Ctrl-C then q to stop). A read-only tmux client cannot scroll (tmux blocks its copy mode).
#   events  the auditor's feed: rig/audit/watch-pi.sh on the newest pi session, one line per notable event (a
#           render/redo/review result, a turn end, a compaction, a failed tool call), forever.
# Read-only; safe during a render.
set -u
newest() { tmux ls -F '#{session_created} #{session_name}' 2>/dev/null | grep -E ' (plant[0-9]+|film[5-9][0-9]*)$' | sort -n | tail -1 | cut -d' ' -f2; }
case ${1:-view} in
  view)
    # a copy of pi's screen redrawn every second, not a tmux client: an attached client, even read-only, makes tmux 3.7
    # refuse the auditor's send-keys to that session ("client is read-only", 2026-09-27 17:09). pi's window is sized to
    # this pane (pi only redraws), and every line is cleared as it is drawn, so nothing wraps or piles up.
    clear; last=""
    while :; do
      s=$(newest)
      if [ -n "$s" ]; then
        size="$COLUMNS x $LINES $s"
        [ "$size" != "$last" ] && { tmux resize-window -t "$s" -x $COLUMNS -y $LINES 2>/dev/null; last=$size; clear; }
        printf '\e[H'; tmux capture-pane -p -e -t "$s" 2>/dev/null | head -n $((LINES - 1)) | sed $'s/$/\e[0m\e[K/'; printf '\e[J'; sleep 1
      else printf "\r[%s] waiting for a pi session (plant<N> or film<N>)..." "$(date +%H:%M:%S)"; sleep 5; fi
    done ;;
  history)
    while :; do s=$(newest); [ -z "$s" ] && { echo "no pi session yet"; sleep 5; continue; }
      tmux capture-pane -p -J -e -S - -t "$s" | less -R +G --prompt="$s history (q = refresh, Ctrl-C then q = stop)"; sleep 1; done ;;
  events)
    D=~/.pi/agent/sessions/-$(echo "$HOME/repos/local-video" | tr / -)--
    while :; do SESSION=$(ls -t $D/*.jsonl | head -1) ~/repos/local-video/rig/audit/watch-pi.sh 900 2>&1 | grep -v '^HEARTBEAT'; done ;;
  *) echo "usage: follow-pi.sh view|history|events"; exit 2 ;;
esac
