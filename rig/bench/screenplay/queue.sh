#!/bin/zsh
E=${0:A:h}; cd $E
./run.sh q4-P0-med prompts/P0-bare.txt vision-q4-400k medium
./run.sh q4-P1-med prompts/P1-format.txt vision-q4-400k medium
./run.sh q4-P2-med prompts/P2-craft.txt vision-q4-400k medium
./run.sh q4-P3-med prompts/P3-revise.txt vision-q4-400k medium
./run.sh q4-P2-off prompts/P2-craft.txt vision-q4-400k off
./run.sh q4-P2-max prompts/P2-craft.txt vision-q4-400k max
./run.sh q2-P2-med prompts/P2-craft.txt vision-500k medium
./run.sh qwen38-P2 prompts/P2-craft.txt qwen38 medium
curl -s 127.0.0.1:8090/unload; echo "QUEUE DONE $(date +%H:%M)"
