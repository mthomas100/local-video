#!/bin/zsh
E=${0:A:h}; cd $E; echo $$ > runs/queue.pid
while [ -e runs/PAUSE ]; do sleep 15; done
./run-skill.sh qwen38-skill qwen38 medium
./run-skill.sh q4-skill vision-q4-400k medium
curl -s 127.0.0.1:8090/unload; echo "QUEUE DONE $(date +%H:%M)"
