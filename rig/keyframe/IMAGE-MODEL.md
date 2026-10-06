# Keyframe image model: Qwen-Image-2.1 on mflux (chosen 2026-09-26)

This is for keyframe-first shots. An image model draws the first frame of a landmark or hero shot as a still.
LTX-2.5 then animates it (`vidgen -i still.png "prompt"`). The goal is to fix the rig's weakest shots, where
landmarks came out as look-alikes: Coit Tower drawn as a thin lighthouse, the Painted Ladies as a flat row of 14
houses, and a generic city in place of the San Francisco skyline.

## The choice and why

**Qwen-Image-2.1** (Alibaba Qwen, open weights released 2026-09-20) runs natively on MLX through **mflux 0.20.0**.

| Part | Detail |
|---|---|
| Generator | 7.1B single-stream, block-causal DiT |
| Text encoder | Qwen3-VL-8B, a vision-language model |
| VAE | 64-channel RGBA VAE with 16x spatial compression |
| Resolution | Native 2K, up to 1536x2752 (9:16) and 2752x1536 (16:9) |
| Sampling | 40 steps, no guidance by default |

How it meets each criterion, in order:

1. **Photorealism and prompt adherence.**
   - It ranks **#1 of the open-weights models in the Artificial Analysis text-to-image arena**, which uses blind
     human votes (independent of Qwen). On 2026-09-26 it had Elo **1035** from 5,151 votes. The models behind it:
     Ideogram 4.0 (1010), FLUX.2 [dev] (1000), Qwen Image Max 2512 (998), HiDream-O1 (979), Z-Image Turbo (940)
     and FLUX.2 [klein] 9B (940).
   - Qwen's own Qwen-Image-Bench scores it 60.28, the best of the downloadable models. That is a vendor
     benchmark.
   - Qwen's release notes and reviewers highlight better portrait lighting, fine detail and very good text
     rendering. Text rendering matters for the brief's billboards.
   - Early users on r/StableDiffusion and r/LocalLLaMA praise its prompt adherence. That is anecdotal.
   - **Landmark knowledge is unproven:** I found no public test of Coit Tower or the Painted Ladies for *any*
     candidate. Two things point in Qwen's favour:
     - The text encoder is a VLM trained to recognise real places.
     - A hands-on review across about a dozen regions found it "generally capturing the right visual style and
       cultural markers", though quality varied from region to region.
   - One comparison (CRITICA) rates Krea 2 Turbo, then Z-Image Turbo, as more natural on skin. Qwen's strengths
     are adherence and composition, which matter more for landmarks.
2. **Runs natively on Apple silicon.**
   - mflux is a line-by-line MLX port that is actively maintained (release 0.20.0 on 2026-09-21).
   - The Qwen-Image-2.1 port (PR #736) was written by Ivan Fioravanti. It has parity tests against the diffusers
     reference: latent mean abs diff 3.6e-4 and channel correlation 0.989-0.992.
   - On an M5 Max, at 1024² and 40 steps in bf16, it measured **about 1.5 s per step and about 78 s per image**.
     The diffusers MPS reference took about 85 s.
   - Width and height must be multiples of 16, so **704x1280 and 1280x704 render natively**, with no crop.
3. **Size: 33.13 GB** in bf16, as published. That is 14.23 GB transformer, 17.53 GB text encoder, 1.35 GB VAE
   and 0.02 GB tokenizer and configs. It fits the 40 GB budget without quantizing. mflux can quantize the
   transformer at load time (`-q 8`), which lowers peak memory but not time.
4. **License: ungated** (`gated: false`, so no HF login is needed), under the **Qwen Research License**.
   - The license allows non-commercial (research or evaluation) use only, which is fine for this personal, local
     rig.
   - This differs from the earlier Apache-2.0 Qwen-Image models. Do not sell the model or build a paid service
     on it without a license from Qwen.
   - Qwen posted a clarification on X about using outputs (see the r/LocalLLaMA license thread), but the LICENSE
     text on HF still says non-commercial only.
5. **Speed:** a 704x1280 image should take about 1 to 1.3 min on this Mac. See the numbers below.

**Fallback, also downloaded (5.91 GB, so both total 39.04 GB): Z-Image Turbo 4-bit**
(`filipstrand/Z-Image-Turbo-mflux-4bit`, the pre-quantized copy made by mflux's author).

- It is a 6B DiT with a Qwen3-4B text encoder and an Apache-2.0 upstream license.
- It needs 9 steps, so it is about 5x faster and good for drafts. It is also a second opinion if Qwen misses a
  landmark.
- The 4-bit copy loses some fine detail compared with bf16. The bf16 upstream is about 31 GB, which would break
  the budget.

## Alternatives considered (one line each)

- **FLUX.2 [dev]** (BFL, Nov 2025; Elo 1000): 32B DiT plus a Mistral-24B text encoder, 177.6 GB repo, gated,
  non-commercial. mflux has no FLUX.2 [dev] port (only klein). Too big.
- **Ideogram 4.0** (Jun 2026; Elo 1010/1003): 9.3B, 27.55 GB FP8 repo, gated, non-commercial. mflux has a CLI.
  It is typography- and design-first with JSON prompts. One review puts it behind FLUX.2 on pure photorealism.
- **HiDream-O1-Image** (2026; Elo 979): 9B pixel-space unified transformer, 35.25 GB, MIT, ungated. There is no
  MLX port (PyTorch or ComfyUI only).
- **Z-Image Turbo** (Tongyi-MAI, Nov 2025; Elo 940): 6B, Apache 2.0, ungated, mature in mflux, 9 steps. It has
  the best "retouched" photoreal look but a smaller text encoder, so less world knowledge. It is the fallback.
- **Krea 2 Turbo** (Jun 2026): 12.9B plus a Qwen3-VL text encoder, 62 GB repo, gated, Krea community license.
  It is in mflux. It has the most natural skin in one comparison but is over budget.
- **FLUX.2 [klein] 9B** (Jan 2026; Elo 940): 52.9 GB repo, gated, non-commercial, in mflux, 4 steps.
- **Qwen-Image-2512** (20B, Dec 2025, Apache 2.0): 57.7 GB in bf16, over budget, and 2.1 beats it in the arena.
  The arena lists a "Qwen Image Max 2512" at 998, and I could not confirm it is the same model.
- **NVIDIA Cosmos3-Super-Text2Image**: 65B, too big.

The gated options (FLUX.2, Ideogram 4, Krea 2) are reachable: this Mac is logged in to HF as `thundacaht`, and
access needs only a click to accept each license on its model page. None of them wins on the criteria above.

## Install (done)

| Item | Detail |
|---|---|
| Runtime | `~/repos/imagegen/.venv`, a separate uv venv. `~/repos/ltx-2-mlx/.venv` and `~/repos/mlx-audio/.venv` are untouched. |
| Packages | Python 3.12.14, **mflux 0.20.0**, mlx 0.32.2, mlx-metal 0.32.2, huggingface-hub 1.33.0, transformers 5.17.0, torch 2.14.0 (a CPU-side dependency of mflux). About 1.1 GB. |
| CLIs | `~/repos/imagegen/.venv/bin/mflux-generate-qwen-2.1` and `.../mflux-generate-z-image-turbo` |
| Not yet run | Not even `--help`, because it imports MLX. Nothing has touched the GPU. |

The commands that built it:

```sh
mkdir -p ~/repos/imagegen && cd ~/repos/imagegen
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python "mflux==0.20.0"
```

## Weights and download status

| Model | Location | Snapshot |
|---|---|---|
| Qwen-Image-2.1 | `~/.cache/huggingface/hub/models--Qwen--Qwen-Image-2.1/` | `790c92633540aa0cb11d9abf19eb46d861714758` |
| Z-Image Turbo 4-bit | `~/.cache/huggingface/hub/models--filipstrand--Z-Image-Turbo-mflux-4bit/` | `b3a8f31115a11f2f9e2fa0bfbc8d78dcc3e6568b` |

mflux finds both models in the HF cache by repo id, so neither needs `--model-path`.

The downloads ran detached and are resumable: rerun the same command to resume. Logs are in `~/repos/imagegen/logs/`.

```sh
nohup hf download Qwen/Qwen-Image-2.1 > ~/repos/imagegen/logs/download-qwen-image-2.1.log 2>&1 &
# chained after it:
hf download filipstrand/Z-Image-Turbo-mflux-4bit   # log: logs/download-z-image-turbo-4bit.log
```

How to check the downloads:

```sh
pgrep -fl "hf download (Qwen|filipstrand)"                                  # still downloading?
du -sh ~/.cache/huggingface/hub/models--Qwen--Qwen-Image-2.1                # about 31 GiB when complete
ls ~/.cache/huggingface/hub/models--Qwen--Qwen-Image-2.1/blobs | grep -c incomplete   # 0 when complete
cat ~/repos/imagegen/logs/download-z-image-turbo-4bit.log                   # "fallback exit=0" when done
hf cache verify Qwen/Qwen-Image-2.1                                        # checksums, after completion
```

If the process dies, rerun the same `nohup hf download Qwen/Qwen-Image-2.1 ...` line. Finished files are
skipped.

## Generate a 704x1280 test image (later, under the GPU rules)

Run it only when no render is running and ds4 `vision` or `vision-q4` is unloaded. Those take 81-91 GB, and this
needs up to about 46 GB.

`HF_HUB_OFFLINE=1` keeps it off the network, so it works with the internet off.

```sh
mkdir -p ~/Videos/keyframes
HF_HUB_OFFLINE=1 ~/repos/imagegen/.venv/bin/mflux-generate-qwen-2.1 \
  --prompt "Coit Tower on Telegraph Hill, San Francisco: a thick fluted white concrete column with a ring of tall arched windows near its top, rising from cypress and eucalyptus trees on the hilltop, at dusk with fog rolling in off the bay and the city lights below. Photorealistic, ordinary 40mm lens, clean full-frame image." \
  --width 704 --height 1280 --steps 40 --seed 42 \
  --output ~/Videos/keyframes/qwen21-coit-704x1280-s42.png --metadata
```

- **Landscape:** use `--width 1280 --height 704`.
- **Several candidates in one call:** `--seed 1 2 3` loads the model once. The output name should contain
  `{seed}`, e.g. `...-s{seed}.png`.
- **Memory:** add `-q 8` when memory is tight. Peak falls to about 31 GB and speed is the same. `--low-ram`
  saves more.
- **Fallback draft:** swap the command for
  `~/repos/imagegen/.venv/bin/mflux-generate-z-image-turbo --model filipstrand/Z-Image-Turbo-mflux-4bit ... --steps 9`
  with the same size, seed and output flags.
- **Animate the still:** `vidgen -i ~/Videos/keyframes/qwen21-coit-704x1280-s42.png "<scene prompt>"`

## Expected speed and memory on this M5 Max

These are estimates from published M5 Max measurements, not yet measured here.

**Speed:**

- A 704x1280 image has 3,520 latent tokens (1024² has 4,096), so expect about **1.3 s per step**.
- 40 steps then take about 55 s. Add about 8-15 s for loading, prompt encoding and VAE decode.
- That gives **about 1-1.3 min per image**, a little more on a cold first load of the 33 GB.
- The measurements this rests on: about 1.5 s/step at 1024² (PR #736), and 1.78 s/step plus about 8 s fixed
  at 1600x672 (Ivan Fioravanti's post on X).
- **If the stills look soft,** the model's native size is 2K, so 0.9 MP is below its sweet spot. Render
  1056x1920 and downscale 1.5x to exactly 704x1280, which takes about 2.5 min per image.

**Memory:**

- Peak is **about 46 GB in bf16** at 1024², or about 31 GB with `-q 8`. The bf16 text encoder (17.5 GB) is never
  quantized.
- It fits beside nothing big: follow the rig's one-GPU-job rule. It cannot share the GPU with an LTX render
  (28-53 GB) or ds4.
- The Z-Image Turbo 4-bit fallback should need about 10 GB and take roughly 15-25 s at 9 steps.

## Risks

- **Runtime maturity.** mflux's Qwen-Image-2.1 port is 5 days old.
  - It has parity tests. The one "purple/green static" report (issue #748) came from a corrupt community 4-bit
    upload, not from the port or the official bf16 weights.
  - The editing / multi-reference mode is **not in mflux yet** (PRs #741, #749 and #766 are open). That mode
    holds identity across up to 10 reference images, which could later help character plates.
  - The text-prefix KV cache is not implemented yet. It is a future speedup.
- **Landmark knowledge is untested.** Test Coit Tower and the Painted Ladies first, still-first against
  text-only, as the handoff says. If Qwen misses, try the Z-Image fallback on the same prompt and seed. Adopt the
  keyframe step only if it wins.
- **License.** Qwen Research (non-commercial) License, not Apache.

## Sources

- Artificial Analysis open-weights text-to-image arena (read 2026-09-26): https://artificialanalysis.ai/image/leaderboard/text-to-image/open-weights
- Model card and files (HF API for sizes, gating, license): https://huggingface.co/Qwen/Qwen-Image-2.1
- Code and README: https://github.com/QwenLM/Qwen-Image-2.1
- Release write-up (architecture, Qwen-Image-Bench 60.28, license): https://www.marktechpost.com/2026/09/21/alibaba-qwen-releases-qwen-image-2-1/
- mflux (supported models, install): https://github.com/filipstrand/mflux (now `mflux-community/mflux`); releases: https://github.com/mflux-community/mflux/releases
- mflux Qwen-Image-2.1 port, with parity, M5 Max timing and peak memory: https://github.com/mflux-community/mflux/pull/736 and https://github.com/mflux-community/mflux/blob/main/src/mflux/models/qwen21/README.md
- The corrupt-4-bit static report: https://github.com/mflux-community/mflux/issues/748
- M5 Max step timings at 1600x672: https://x.com/ivanfioravanti/status/2101257247292580045
- M4 Max user report (6 s/step at 1024²; quantization gives no speedup): https://github.com/The-Focus-AI/qwen-image-2.1-mlx
- Mac runtime survey: https://modelfit.io/blog/qwen-image-2-1-mac-apple-silicon/
- Comparison of Z-Image, FLUX.2 Klein, Qwen Image 2.1 and Krea 2 (licenses, realism): https://www.criticatv.com/z-image-vs-flux-klein-vs-qwen-image-krea-2-comfyui/
- Hands-on review (cultural accuracy across regions): https://www.mindstudio.ai/blog/qwen-image-2-1-hands-on-review
- Review (text rendering, sizes): https://www.eesel.ai/blog/qwen-image-2-1-review
- Community reports: https://old.reddit.com/r/StableDiffusion/comments/1wnqy2k/ , https://old.reddit.com/r/LocalLLaMA/comments/1wlgrft/ , license thread https://old.reddit.com/r/LocalLLaMA/comments/1wm4o8x/
- Fallback: https://huggingface.co/filipstrand/Z-Image-Turbo-mflux-4bit and https://huggingface.co/Tongyi-MAI/Z-Image-Turbo
- Alternatives:
  - Ideogram 4: https://huggingface.co/ideogram-ai/ideogram-4-fp8 and https://ideogram.ai/blog/ideogram-4.0/
  - HiDream-O1: https://huggingface.co/HiDream-ai/HiDream-O1-Image
  - Krea 2: https://www.krea.ai/blog/krea-2-technical-report
  - FLUX.2: https://huggingface.co/black-forest-labs/FLUX.2-dev

## Measured on this Mac (2026-09-26, iteration 3)

- **Speed:** 3 stills at 704x1104 and 40 steps in one call took 137-157 s (model load included); a single
  still took 46-48 s. A still at 704x1280 through `bin/still`: see the iteration-3 notes (not published).
- **Quality:** Coit Tower right in 3 of 3 seeds (the thick fluted column, the ring of arched windows, the
  wooded hill, the bay); the Painted Ladies right in 3 of 3 (the gabled row, the skyline behind); a painted
  clown drawn with one face, paint and costume in three compositions from one sentence. It paints
  pseudo-text on neon signs even when the prompt says "no text".
- **Adopted** as keyframe-first for landmark and recurring-character shots: the `[still]` token in
  `stories/story.sh`, drawn by `bin/still`. Evidence: `skills/film/references/prompt-rules.md`,
  "Keyframe-first". Z-Image Turbo (the fallback) was not needed.

## FLUX.2 klein 4B for reference edits (added 2026-09-27, iteration 4)

**Why a second image model.** Qwen-Image-2.1 draws each still from text alone, so a recurring character got a new face
in every shot (halloween-clowns-sf-portrait: Marrow about five faces, Tatter four in four shots), and its
image-to-image never adds people to a reference photo (tested at strengths 0.15-0.75 on the human's hotel corridor).
FLUX.2 klein 4B (Black Forest Labs, Apache-2.0, about 15 GB, `mflux-generate-flux2-edit --model flux2-klein-4b`)
edits with several reference images at once.

**Measured on this Mac** (704x1280, offline): a cast portrait with Qwen 55 s; a klein composition 16 s. The father
clown's portrait composed into a pool-corridor reference photo (wading, looking back) and backrooms photo (close-up,
speaking) kept the same long face, grey stubble, receding hair, white paint, red nose, powder-blue satin suit and
pom-pom buttons, and each room matched its photo. Through story.sh (`00-place-smoke`, 480p): the composed frame
animated as a speaking close-up, lip sync corr 0.45 at -42 ms.

**How the rig uses it.** `CAST=( "name|sentence" )` draws each portrait once per film (Qwen, `bin/still --portrait`);
`[cast=a,b]` composes the shot's first frame from `[place]` (if given) plus the portraits (`bin/still --ref`).
Download note: the Xet transfer stalled twice at 2.4 GB; `HF_HUB_DISABLE_XET=1 hf download` finished it.
