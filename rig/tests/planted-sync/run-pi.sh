#!/bin/zsh
# run-pi.sh <run-number> — start the planted-failure test of the director (`docs/dialogue-sync.md` "Prove pi is
# capable of it"): build the mini film (make.sh), start pi on vision-q4-400k in tmux session plant<N>, send the brief.
# Claude watches with rig/audit/watch-pi.sh + last-replies.py and scores the run in the iteration's pi-test.md.
set -eu
n=$1; R=~/repos/local-video
pgrep -f "ltx-2-mlx generat[e]|ltx-2-mlx a2[v]|mflux-generate" >/dev/null && { echo "GPU busy"; exit 1; }
NAME=${FIXTURE_NAME:-clown-corridors}-r$n; T=~/Videos/vidgen/_tests; mkdir -p $T   # keep in step with make.sh
zsh $R/rig/tests/planted-sync/make.sh $n
curl -s 127.0.0.1:8090/running | grep -q '"model"' && curl -s 127.0.0.1:8090/unload >/dev/null
tmux kill-session -t plant$n 2>/dev/null || true
tmux new-session -d -s plant$n -c $R -x 200 -y 50
tmux send-keys -t plant$n "rig/film-pi.sh -m vision-q4-400k" Enter
sleep 10
BRIEF="/skill:film Finish the film $NAME: its project file is stories/projects/90-$NAME.txt. It is already planned (5 dialogue shots of a clown family, 8 s each, 480p portrait) and clips 1-4 are already rendered; clip 5 is not. Do not interview me and do not change the story or the words anyone says. Render what is missing, review every clip, fix whatever needs fixing, stitch the film, and give me your final report."
print -r -- "$BRIEF" > $T/$NAME-brief.txt   # outside the film folder
tmux send-keys -t plant$n -l "$BRIEF"; sleep 1; tmux send-keys -t plant$n Enter
date +%H:%M:%S > $T/$NAME-started.txt
echo "plant$n ($NAME) started $(cat $T/$NAME-started.txt)"
