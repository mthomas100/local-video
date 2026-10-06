# Screenplay eval, 2026-10-03: which prompt, effort and local model writes the best film screenplay?

**Task.** Every run got the same input: the Clown Sighting brief (`brief.txt`, paraphrased in this public copy). The brief asks for a
~3-minute 9:16 local-news report from San Francisco, a clown always in the background and unnoticed, Halloween,
and every shot fully directed.

**Harness.** One pi run per cell (`run.sh`):
- a fixed neutral system prompt;
- only the read, write and edit tools;
- no skills, extensions or context files;
- the screenplay written to a file.

**Scoring.** Two kinds:
- mechanical: `score.py`;
- blind: two judges, Claude Opus 5.5 and Claude Fable 5.1, read all 8 screenplays under shuffled letters, scored them
  1-10 on 5 criteria (`judge-rubric.md`) and ranked them.

Claude Code's own screenplay (the one Clown Sighting was made from) was in the blind set as a reference.

## Results (n = 1 run per cell: a direction, not a measurement)

| screenplay | prompt | model | thinking | time | Opus /50 | Fable /50 | total | funny (O/F) | lint | clown in bg |
|---|---|---|---|---|---|---|---|---|---|---|
| Claude Code (reference) | - | Claude Opus 5.5 | - | - | 39 (1st) | 43 (1st) | **82** | 8/8 | 0 | 18/18 |
| qwen38-P2 | P2 craft | Qwen3.8 Flash Next | on | 622 s | 37 (2nd) | 40 (2nd) | **77** | 7/8 | 10 | 17/17 |
| q4-P2-med | P2 craft | DeepSeek V4 Flash Vision Q2/Q4 | full | 755 s | 32 (3rd) | 34 (3rd) | 66 | 5/6 | 0 | 21/21 |
| q4-P3-med | P3 craft + self-revise | DeepSeek Q2/Q4 | full | 810 s | 30 | 31 | 61 | 4/5 | 21 | 21/21 |
| q2-P2-med | P2 craft | DeepSeek Q2 (vision-500k) | full | 669 s | 30 | 28 | 58 | 5/5 | 8 | 8/8 |
| q4-P2-max64k | P2 craft | DeepSeek Q2/Q4 | Think Max, 64K reply cap | 909 s | 26 | 29 | 55 | 3/5 | 21 | 21/21 |
| q4-P0-med | P0 bare | DeepSeek Q2/Q4 | full | 310 s | 23 | 27 | 50 | 6/7 | 0 | 5/6 |
| q4-P1-med | P1 format only | DeepSeek Q2/Q4 | full | 836 s | 22 (last) | 22 (last) | 44 | 2/3 | 0 | 21/21 |
| q4-P2-off | P2 craft | DeepSeek Q2/Q4 | off | 41 s | - | - | no output | | | |
| q4-P2-max-16k | P2 craft | DeepSeek Q2/Q4 | Think Max, 16K cap | 472 s | - | - | no output | | | |

The two "no output" rows:
- **thinking off:** narrated its plan ("Let me write it now") and ended the turn without calling the write tool;
- **Think Max at the shared 16,384-token reply cap:** all 16,384 tokens went to thinking, then a length stop with no
  text.

## What it says

1. **The prompt matters most, and craft matters more than format.**
   - Format-only (P1) gave the most rig-compliant screenplay and the least funny one: last for both judges.
     - The clown speaks.
     - The reporter explains the gag ("He's always right behind them").
     - Every background only illustrates the line.
   - Adding the comedy method (P2) raised funny from 2-3 to 5-6 on the same model.
   - The bare brief (P0) is funnier than format-only but unusable on the rig:
     - 35 s multi-speaker shots;
     - the reporter turns to look at the clown every time;
     - 3:25 long.
2. **A self-revision pass did not help** (P3 61 vs P2 66). It also moved the delivery cues after the quotes, which the
   rig's lint rejects (21 findings).
3. **More thinking did not help.**
   - Think Max came out 7th of 8 and 5th of 8, and was the slowest.
   - At the rig's 16K reply cap it produces nothing at all.
   - Thinking off produces nothing either.
   - Default thinking is best.
4. **The best local writer is Qwen3.8 Flash Next:** close to the reference (77 vs 82) and the fastest full run.
   - Its tic: every witness gets the same dropped-s dialect ("He ride my bus. He pay exact change.").
   - Its background gags are too intricate to read small on a phone.
   - DeepSeek Q2 is weaker than Q2/Q4 at the same prompt (58 vs 66) and dropped the clown from most shots.
5. **What separates the top two, per both judges:**
   - Each line is a real grievance or affection, with a turn in its last words.
   - The background comments on the line (contradicts it, quietly confirms it, or one-ups it) instead of illustrating
     it.
   - The conceit holds to the end: nobody notices, the clown never speaks.
   - The button is one silent image that the line before it sets up.
   - Common failures elsewhere: the reporter notices the clown, the clown speaks or explains himself, broken broadcast
     order, an ending image with no joke.

## Judge notes

**About the outputs.** Every screenplay under `runs/` and `judge*/` is kept unedited as benchmark evidence, including lines the judges penalised as stereotyped accent jokes (for example the dropped-s dialect qwen38-P2 gives the bus driver and other witnesses). That is a judged failure, not an endorsement.

Verbatim, decoded with the key `A=q4-P2-max64k B=q2-P2-med C=q4-P2-med D=q4-P0-med E=q4-P1-med F=qwen38-P2
G=q4-P3-med H=claude`. They are in `judge-opus.md` and `judge-fable.md`.

## Reproduce

- `queue4.sh`-style runs: `./run.sh <name> prompts/<P>.txt <llama-swap row> <thinking>`.
- Think Max at a 64K reply cap needs a private pi config: copy `~/.pi/agent/models.json` and `settings.json` into a
  folder, set the row's `maxTokens` to 65536 and `contextWindow` to 334464, then run with `PI_CODING_AGENT_DIR=<that
  folder>` (git-ignored as `agent-bigout/`).
- Session files are not kept in git; each run's `timeline.jsonl` is the metadata-only copy (`rig/audit/session-timeline.py`).

## Round 2: does the screenplay skill help? (2026-10-03 evening) — no, not yet

**Setup.**
- Skill v1 (commit 8afb4b2) made both models fail: each spent its whole 16K reply thinking and wrote nothing
  (`runs/*-skill-v1-nowrite`).
- Skill v2 (0f8e0fa, "think on paper in short replies") wrote complete screenplays.
- Five screenplays were judged blind again (`judge2/`, key in `judge2/KEY.json`).

| screenplay | Opus /50 | Fable /50 | total | lint |
|---|---|---|---|---|
| Claude Code (reference) | 41 (1st) | 43 (2nd) | **84** | 0 |
| qwen38 + P2 craft prompt (round 1) | 40 (2nd) | 41 (1st) | **81** | 10 |
| qwen38 + skill v2 | 34 | 39 | 73 | 0 |
| DeepSeek Q2/Q4 + P2 craft prompt (round 1) | 32 | 27 | 59 | 0 |
| DeepSeek Q2/Q4 + skill v2 | 22 (last) | 23 (last) | 45 | 0 |

**What it says** (n = 1 per cell):
- The skill fixed the rig compliance (lint 0, the clown behind every speaker) but made both models less funny than the
  shorter P2 prompt.
- **Contamination.** The skill's examples are Clown Sighting's own jokes ("I don't even like that car", the balloon,
  "the clown is the weatherman"), and the validation used the same brief.
  - DeepSeek's skill run reused the weatherman button and gave it away in shot 1.
  - It stamped one formula onto many witnesses.
- **Next:**
  - draw the skill's examples from other films and genres;
  - shorten it to P2's length;
  - keep P2's lighter process (brainstorm "in your head or in notes", write in parts);
  - validate on a held-out brief (not the clown film), with 2 runs per cell.
  - Until then, the round-1 P2 prompt (`prompts/P2-craft.txt`) on qwen38 is the best local recipe measured.

Verbatim judge outputs: `judge2-opus.md`, `judge2-fable.md`.

## Round 3: skill v3 on a held-out brief (2026-10-04), 2 runs per cell — the skill matches the best prompt and is rig-ready

**Setup.**
- Brief: `brief2.txt`, a hushed nature-documentary parody about a San Francisco startup in Halloween week. Neither
  the skill nor the prompts were written for it.
- Prompt arm: P2g, the generic craft prompt.
- Skill arm: v3, frozen in `frozen-skill-v3/` because another session edited the live skill mid-queue.
- Judging: blind, two judges (`judge3/`, key in `judge3/KEY.json`; verbatim in `judge3-*.md`).

| screenplay | Opus /50 | Fable /50 | total | lint | time |
|---|---|---|---|---|---|
| qwen38 + P2g, run 1 | 40 (1st) | 42 (1st) | 82 | 8 | 461 s |
| qwen38 + skill v3, run 1 | 38 (2nd) | 40 (3rd) | 78 | 0 | 506 s |
| qwen38 + skill v3, run 2 | 36 | 40 (2nd) | 76 | 0 | 467 s |
| qwen38 + P2g, run 2 | 31 | 38 | 69 | 17 | 334 s |
| DeepSeek Q2/Q4 + P2g, run 1 | 24 | 24 | 48 | 0 | 489 s |
| DeepSeek Q2/Q4 + P2g run 2, skill v3 runs 1 and 2 | - | - | no output | | |

**Findings.**
- **On qwen38 the skill matches the craft prompt** (means 77 vs 75.5) with less spread and 0 lint findings, against 8
  and 17. On this rig that is the better choice.
- **Skill run 2 was contaminated by the checker.** score.py then counted clowns, and the model, told to fix what the
  checker names, added "a silent office clown" to every shot. Both judges still placed it 2nd-3rd.
  - Fixed in 8ed7d31: score.py is brief-neutral, with opt-in `--bg`/`--theme`.
  - Skill run 1 also read `stories/screenplays/clown-sighting.md` while exploring the repo.
- **DeepSeek V4 Flash Vision at the rig's 16K reply cap is an unreliable writer.**
  - At default thinking, across all rounds, 4 of 10 screenplay runs ended with a reply that spent all 16,384 tokens
    thinking and wrote nothing (skill v1, brief2 P2g run 2, brief2 skill runs 1 and 2).
  - Its finished screenplays score far below qwen38: 48 here; 59 and 66 in rounds 1-2.
  - qwen38 failed once in 7 runs, on skill v1 before the think-on-paper fix.
- **The rubric still said "news broadcast"** in two criteria. Both judges noticed and judged against the
  documentary's spine.

**Recommendation.** Write screenplays with Qwen3.8 Flash Next and skill v3. The director (DeepSeek, needed for its
vision) should not write them at a 16K reply cap. Options: a rig tool that runs the screenplay step on qwen38, the
way the render tools swap models in; or a larger reply cap for the director (Think Max at 64K finished once, but
scored low).
