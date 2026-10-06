// film-rig.ts — pi extension for the local-agent film rig (2026-09-23).
//
// Three tools for a LOCAL model orchestrating LTX-2.5 renders on this one Mac, where the model and
// the renderer cannot share the GPU (an LLM prompted beside a render slows it 9x and never answers;
// two renders at once swap 27 GB; the overnight-run notes (not published)):
//
//   render_and_wait <project> [until_scene] [sheet]  preflight, unload the LLM (alternation mode),
//       wait for memory to settle, launch stories/run-queue.sh DETACHED, block the whole turn until
//       queue.log says OK|FAILED|PAUSED, then return timings, the story-log tail and rig/precheck.py's
//       verdicts with audio transcripts, as TEXT (since 2026-09-24: an image in the wake request made
//       ds4 skip its disk cache). The model is reloaded by llama-swap on the very next request, which is
//       the "wake"; ds4's disk KV checkpoints make that a suffix prefill.
//   review_scenes <name> <scenes>                     sheets as images (shown once) + pre-checks, no render.
//   redo_scenes <project> <scenes>                    stories/redo.sh on ONLY those scenes, same wait and report.
//
// Guards, because the rules were paid for: every tool refuses while a render runs; a bash command
// that would start a render, touch a model server or kill anything is blocked (tool_call); an LLM
// call is held while a render process exists (context, before_agent_start), so nothing prompts the
// model mid-render even if the render was started elsewhere; auto-compaction is cancelled while a
// render runs (session_before_compact). Modes: FILM_RIG_MODE=alternate (default: /unload before
// each render) or resident (keep the LLM loaded, e.g. qwen27-262k beside a 480p render; nothing may
// prompt it until the render ends, which the blocking tool guarantees).
//
// /film [brief|off|status] (2026-09-23 evening): enter director mode in ANY pi session with whatever
// model it already has: the director prompt (rig/film-director.md) is appended to the system prompt on
// every turn, the choice is persisted in the session (survives -c), and a brief given with the command
// is sent as the first message. No model switching: a warning if the model cannot see images.
// Lifecycle follows the active model's provider: "local" = llama-swap (GET /unload, reload on demand);
// "ds4"/"qwen" = an engine the human started with `model <target>` (ds4-serve), which the render tool
// stops with `model stop` before a render and restarts with `model <target>` after, so the next reply works.
//
// Installed by symlink: ~/.pi/agent/extensions/film-rig.ts -> ~/repos/local-video/rig/film-rig.ts
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { spawn } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import { homedir } from "node:os";

const HOME = homedir();
const REPO = path.join(HOME, "repos/local-video");
const VIDEOS = path.join(HOME, "Videos/vidgen");
const QUEUE_LOG = path.join(REPO, "logs/queue.log");
const SWAP = process.env.FILM_RIG_SWAP ?? "http://127.0.0.1:8090";
const WIRED_MAX_GB = Number(process.env.FILM_RIG_WIRED_MAX_GB ?? 40);
const POLL_MS = 15_000;
const MAX_WAIT_MS = 8 * 3600_000;

const mode = () => (process.env.FILM_RIG_MODE === "resident" ? "resident" : "alternate");
const DS4_DIR = path.join(HOME, "repos/ds4");
const DIRECTOR_MD = path.join(REPO, "rig/film-director.md");
const DIRECTOR_MARKER = "You are the film director on this Mac";

interface ActiveModel { provider: string; id: string; input?: string[] }
let director = false;                      // /film on|off, persisted as a "film-rig" session entry
let directorPrompt_seen = false;           // rig/film-pi.sh appends the director prompt itself, without /film
// Director mode: /film, /skill:studio or /skill:film, rig/film-pi.sh (FILM_RIG_DIRECTOR=1), or the director prompt in
// the system prompt. The film-only rules (the full bash blocklist, images shown once) apply only then (2026-10-04).
export const isDirector = () => director || directorPrompt_seen || process.env.FILM_RIG_DIRECTOR === "1";
let activeModel: ActiveModel | undefined;  // from session_start and model_select
let restartAfterRender: { target: string } | null = null; // set when a ds4-serve engine was stopped for a render

// "swap": the model is served by llama-swap (provider "local"); unload = GET /unload, reload on demand.
// "ds4-serve": the human started it with `model <target>`; unload = `model stop`, reload = `model <target>`.
function lifecycle(): "swap" | "ds4-serve" {
  const pr = activeModel?.provider ?? "local";
  return pr === "ds4" || pr === "qwen" ? "ds4-serve" : "swap";
}
const modelSeesImages = () => !activeModel || (activeModel.input ?? []).includes("image");

let directorCache: { mtime: number; text: string } | null = null;
function directorPrompt(): string {
  try {
    const mtime = fs.statSync(DIRECTOR_MD).mtimeMs;
    if (!directorCache || directorCache.mtime !== mtime) {
      const raw = fs.readFileSync(DIRECTOR_MD, "utf8");
      const body = raw.startsWith("---") ? raw.replace(/^---[\s\S]*?\n---\n?/, "") : raw;
      directorCache = { mtime, text: body.trim() };
    }
    return directorCache.text;
  } catch (e) {
    return `(film-director.md could not be read: ${e}; follow the film skill, section 0)`;
  }
}

// `model status --porcelain` from the human's control panel (key=value lines); target= is the loaded model.
async function ds4ServeStatus(): Promise<Record<string, string>> {
  const r = await run(path.join(DS4_DIR, "model"), ["status", "--porcelain"], { cwd: DS4_DIR, timeoutMs: 20_000 });
  const out: Record<string, string> = {};
  for (const line of r.stdout.split("\n")) { const i = line.indexOf("="); if (i > 0) out[line.slice(0, i).trim()] = line.slice(i + 1).trim(); }
  return out;
}

interface Run { code: number; stdout: string; stderr: string }
interface ImagePart { type: "image"; data: string; mimeType: string }
interface TextPart { type: "text"; text: string }

// ---------- process and system helpers (argv arrays, no shell) ----------

function run(cmd: string, args: string[], opts: { cwd?: string; timeoutMs?: number; signal?: AbortSignal; env?: NodeJS.ProcessEnv } = {}): Promise<Run> {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, { cwd: opts.cwd ?? REPO, shell: false, stdio: ["ignore", "pipe", "pipe"], env: opts.env ?? process.env });
    let stdout = "", stderr = "";
    child.stdout.on("data", (d) => (stdout += d.toString()));
    child.stderr.on("data", (d) => (stderr += d.toString()));
    const timer = setTimeout(() => child.kill("SIGTERM"), opts.timeoutMs ?? 120_000);
    const onAbort = () => child.kill("SIGTERM");
    opts.signal?.addEventListener("abort", onAbort, { once: true });
    child.on("error", (e) => { clearTimeout(timer); resolve({ code: 127, stdout, stderr: stderr + String(e) }); });
    child.on("close", (code) => { clearTimeout(timer); opts.signal?.removeEventListener("abort", onAbort); resolve({ code: code ?? 1, stdout, stderr }); });
  });
}

const sleep = (ms: number, signal?: AbortSignal) => new Promise<void>((res) => {
  const t = setTimeout(res, ms);
  signal?.addEventListener("abort", () => { clearTimeout(t); res(); }, { once: true });
});

async function pgrep(args: string[]): Promise<number[]> {
  const r = await run("pgrep", args, { timeoutMs: 10_000 });
  return r.stdout.split("\n").map((s) => parseInt(s, 10)).filter((n) => !Number.isNaN(n));
}

// Render processes: the MLX engine and the runner scripts (a runner without an engine is between scenes).
async function renderProcs() {
  const engine = await pgrep(["-f", "ltx-2-mlx generat[e]"]);
  const runners = await pgrep(["-f", "run-queue[.]sh|story[.]sh|redo[.]sh"]);
  return { engine, runners, any: engine.length + runners.length > 0 };
}

async function modelServers() {
  return { ds4: await pgrep(["-x", "ds4-server"]), llama: await pgrep(["-x", "llama-server"]) };
}

async function wiredGB(): Promise<number> {
  const r = await run("vm_stat", [], { timeoutMs: 10_000 });
  const page = Number(/page size of (\d+) bytes/.exec(r.stdout)?.[1] ?? 16384);
  const wired = Number(/Pages wired down:\s+(\d+)/.exec(r.stdout)?.[1] ?? 0);
  return Math.round((page * wired) / 1e9 * 10) / 10;
}

// The kernel's system-wide free-memory percentage (what memory_pressure prints). A render peaks near 61 GB at 720p;
// on 2026-09-25 another app's GPU leak left 4% free while only 24.6 GB was wired, which the wired check cannot see.
async function memoryFreePct(): Promise<number> {
  const r = await run("sysctl", ["-n", "kern.memorystatus_level"], { timeoutMs: 5_000 });
  const n = parseInt(r.stdout.trim(), 10);
  return Number.isNaN(n) ? 100 : n;
}

async function swapRunning(): Promise<string[] | "unreachable"> {
  try {
    const res = await fetch(`${SWAP}/running`, { signal: AbortSignal.timeout(5000) });
    const j = (await res.json()) as { running?: { model: string; state?: string }[] };
    return (j.running ?? []).map((m) => m.model + (m.state ? `:${m.state}` : ""));
  } catch {
    return "unreachable";
  }
}

async function preflight() {
  const [procs, servers, wired, running, free] = await Promise.all([renderProcs(), modelServers(), wiredGB(), swapRunning(), memoryFreePct()]);
  const df = await run("df", ["-h", HOME], { timeoutMs: 10_000 });
  const queueTail = fs.existsSync(QUEUE_LOG) ? fs.readFileSync(QUEUE_LOG, "utf8").trim().split("\n").slice(-3) : [];
  return {
    mode: mode(),
    lifecycle: lifecycle(),
    director,
    model: activeModel ? `${activeModel.provider}/${activeModel.id}${modelSeesImages() ? "" : " (NO image input)"}` : "unknown",
    render_processes: procs,
    model_servers: servers,
    llama_swap_running: running,
    wired_gb: wired,
    memory_free_pct: free,
    disk: df.stdout.trim().split("\n").pop() ?? "",
    queue_tail: queueTail,
    at: new Date().toISOString(),
  };
}

// Alternation: unload everything behind llama-swap and wait until nothing is loaded and wired memory
// is back under the threshold. An idle ds4 vision server kept ~90 GB wired for 18 h on 2026-09-23 and
// /running alone did not show it, hence the pgrep and vm_stat checks. Never SIGKILLs anything.
async function unloadAndSettle(onUpdate: (s: string) => void, signal?: AbortSignal) {
  const t0 = Date.now();
  const lc = lifecycle();
  if (mode() === "alternate") {
    if (lc === "ds4-serve") {
      // The human's `model <target>` engine: stop it through their control panel (SIGTERM + wait inside
      // ds4-serve, never -9) and remember the target so the render tool can bring it back afterwards.
      const st = await ds4ServeStatus();
      const target = st.target || "";
      onUpdate(`stopping the ds4-serve engine ${target || "(unknown target)"} with \`model stop\``);
      const r = await run(path.join(DS4_DIR, "model"), ["stop", "--yes"], { cwd: DS4_DIR, timeoutMs: 300_000 });
      if (r.code !== 0) onUpdate(`model stop exited ${r.code}: ${(r.stderr || r.stdout).trim().slice(-300)}`);
      if (target) restartAfterRender = { target };
    } else {
      try { await fetch(`${SWAP}/unload`, { signal: AbortSignal.timeout(300_000) }); } catch (e) { onUpdate(`unload request failed: ${e}`); }
    }
  }
  for (let i = 0; i < 40 && !signal?.aborted; i++) {
    const [running, servers, wired] = await Promise.all([swapRunning(), modelServers(), wiredGB()]);
    const loaded = running !== "unreachable" && running.length > 0;
    const strangers = servers.ds4.length > 0 || (mode() === "alternate" && servers.llama.length > 0);
    const ok = mode() === "resident" ? !servers.ds4.length : !loaded && !strangers && wired < WIRED_MAX_GB;
    if (ok) {
      const free = await memoryFreePct();
      const warning = free < 45 ? `only ${free}% of memory is free after unloading the model: another process holds memory (check \`top -o mem\`); the render may swap and run slowly` : undefined;
      if (warning) onUpdate(`warning: ${warning}`);
      return { ok: true, seconds: Math.round((Date.now() - t0) / 1000), wired_gb: wired, memory_free_pct: free, running, lifecycle: lc, ...(warning ? { warning } : {}) };
    }
    onUpdate(`settling: running=${JSON.stringify(running)} ds4=${servers.ds4.length} llama=${servers.llama.length} wired=${wired} GB (${Math.round((Date.now() - t0) / 1000)} s)`);
    await sleep(10_000, signal);
  }
  const wired = await wiredGB();
  const servers = await modelServers();
  const hint = servers.ds4.length && lc === "swap"
    ? " A ds4-server outside llama-swap is running (started with `model <target>`): either use that model in pi (then /film handles it) or stop it with `model stop`."
    : "";
  return { ok: false, seconds: Math.round((Date.now() - t0) / 1000), wired_gb: wired, running: await swapRunning(), lifecycle: lc, hint };
}

// After a render in ds4-serve lifecycle: bring the human's engine back so the very next reply works.
async function restartEngineIfNeeded(onUpdate: (s: string) => void): Promise<string> {
  const r = restartAfterRender; restartAfterRender = null;
  if (!r) return "";
  const t0 = Date.now();
  onUpdate(`restarting ${r.target} with \`model ${r.target}\` (ds4-serve waits for it to be ready)`);
  const res = await run(path.join(DS4_DIR, "model"), [r.target, "--yes"], { cwd: DS4_DIR, timeoutMs: 600_000 });
  const secs = Math.round((Date.now() - t0) / 1000);
  if (res.code !== 0) return `Engine restart FAILED (\`model ${r.target}\` exited ${res.code} after ${secs} s): ${(res.stderr || res.stdout).trim().slice(-400)}. Run \`model ${r.target}\` in a terminal before the next reply.`;
  return `The model engine was stopped for the render and restarted with \`model ${r.target}\` (${secs} s); pi's catalog was merged, not replaced.`;
}

// ---------- project and film helpers ----------

// The scene lines: double-quoted lines inside SCENES=( ... ) only (2026-09-27: CAST=( "name|..." ) lines are quoted too;
// counting every quoted line made liminal-clowns 25 scenes instead of 22 and redo_scenes reported FAILED).
export function sceneLines(txt: string): string[] {
  const m = /^SCENES=\(\s*\n([\s\S]*?)^\)/m.exec(txt);
  return ((m ? m[1] : txt).match(/^"(.*)"$/gm) ?? []);
}

// The sync gate's current verdicts from a story log: the latest "sync N:" line per shot, then any "scene N: no take
// passed / kept" line, in the order they were last written (2026-09-27, planted test run 1: the log keeps every earlier
// verdict and the runner writes each line twice, so a redo's result showed the old FAIL lines above the new PASS ones).
export function latestSyncLines(log: string): string[] {
  const last = new Map<string, string>();
  for (const l of log.split("\n")) {
    const m = /^sync (\d+): /.exec(l) ?? /^scene (\d+): (?:no take passed|kept)/.exec(l);
    if (!m) continue;
    const k = (l.startsWith("sync") ? "sync " : "scene ") + m[1];
    last.delete(k); last.set(k, l);
  }
  return [...last.values()].slice(-40);
}
function resolveProject(p: string) {
  const abs = path.isAbsolute(p) ? p : path.join(REPO, p.replace(/^@/, ""));
  if (!fs.existsSync(abs)) throw new Error(`no project file at ${abs} (expected stories/projects/NN-<slug>.txt)`);
  const txt = fs.readFileSync(abs, "utf8");
  const name = /^NAME=([\w-]+)/m.exec(txt)?.[1];
  if (!name) throw new Error(`${abs}: no NAME=<slug> line`);
  const scenes = sceneLines(txt).length;
  const size = /\bSIZE=(\w+)/.exec(txt)?.[1] ?? "720p";
  const portrait = /\bPORTRAIT=1\b/.test(txt);
  const secs = Number(/\bSECS=(\d+)/.exec(txt)?.[1] ?? 15);
  return { abs, name, scenes, size, portrait, secs, dir: path.join(VIDEOS, name) };
}

// The flat-direction lint (rig/dialogue.py lint, 2026-09-27 iteration 5): a spoken line directed only with "in a X voice",
// with no face or body cue before the speech verb, or with the previous line's delivery, and a BIBLE that freezes the
// actors, are refused before any GPU time is spent (liminal-clowns: all ten lines were directed that way and the
// human heard them as flat or awkward). Since 2026-10-04 it also refuses "he says" / "she says" when the shot
// describes two people the pronoun fits (`--who`): the iteration-9 film, shot 3, gave the king's line to the minister, and the
// sync gate passed it because only one mouth moved.
async function lintDialogue(abs: string, scenes: number[] = []): Promise<void> {
  const r = await run("python3", [path.join(REPO, "rig/dialogue.py"), "lint", "--who", abs, ...scenes.map(String)], { timeoutMs: 30_000 });
  if (r.code === 1 && r.stdout.trim()) {
    throw new Error(`Not rendered: the spoken lines are not directed yet (how: skills/film/references/performance.md; who speaks: skills/film/references/dialogue-shots.md). Fix these in ${path.basename(abs)}, then call the tool again:\n${r.stdout.trim()}`);
  }
}

async function checkSyntax(abs: string) {
  const r = await run("zsh", ["-n", abs], { timeoutMs: 20_000 });
  if (r.code !== 0) throw new Error(`zsh -n ${abs} failed:\n${r.stderr}`);
}

// The prompt, seed and mode story.sh would use for scene n (tokens parsed the way story.sh does), compared
// with the vidgen sidecar of the current take. Returns a short reason when they are identical, "" otherwise.
const SCENE_OF = 'MODE=""; SOUND=""; source "$1"; print -r -- "${SCENES[$2]}"; print -r -- "$BIBLE"; print -r -- "$SEED"; print -r -- "$MODE"; print -r -- "$SOUND"';
// Whether the clip on disk for scene n was rendered from the line, seed and mode the project asks for now:
// same true/false, or null when there is no sidecar to tell (a clip made outside vidgen).
export async function lastTakeVsLine(abs: string, dir: string, n: number): Promise<{ same: boolean | null; why: string }> {
  const side = path.join(dir, `scene-${n}.json`);
  if (!fs.existsSync(side)) return { same: null, why: "no sidecar" };
  const r = await run("zsh", ["-c", SCENE_OF, "_", abs, String(n)], { timeoutMs: 20_000 });
  if (r.code !== 0) return { same: null, why: "the project does not source" };
  const [line = "", bible = "", seed = "", projMode = "", sound = ""] = r.stdout.split("\n");
  let s = line, seedN = seed.trim();
  let mode = projMode.trim() === "--quality" ? "quality" : projMode.trim() === "--hq" ? "hq" : "fast";
  for (let m = /^\[([^\]]*)\] ?/.exec(s); m; m = /^\[([^\]]*)\] ?/.exec(s)) {
    if (m[1].startsWith("seed=")) seedN = m[1].slice(5);
    if (m[1] === "quality" || m[1] === "fast") mode = m[1];
    s = s.slice(m[0].length);
  }
  try {
    const j = JSON.parse(fs.readFileSync(side, "utf8")) as { prompt?: string; seed?: number; line_seed?: number; mode?: string };
    // story.sh appends " Sound: $SOUND" to the video prompt since 2026-09-27; without it here the guard called every
    // clip of liminal-clowns stale and render_and_wait refused to continue the film.
    const asked = `${s} ${bible}`, withSound = sound.trim() ? `${asked} Sound: ${sound.trim()}` : asked;
    // a sync retake (story.sh, 2026-09-27) renders the line at another video seed and records the line's seed as line_seed
    const same = (j.prompt === asked || j.prompt === withSound) && String(j.line_seed ?? j.seed) === seedN && (j.mode ?? "fast") === mode;
    return { same, why: same ? `seed ${seedN}, ${mode} mode` : "a different line, seed or mode" };
  } catch { return { same: null, why: "unreadable sidecar" }; }
}
export async function unchangedSinceLastTake(abs: string, dir: string, n: number): Promise<string> {
  const v = await lastTakeVsLine(abs, dir, n);
  return v.same === true ? v.why : "";
}
// Scenes whose clip on disk was rendered from another line than the project's (2026-09-26). story.sh skips every
// scene whose clip exists, so a project that reuses an earlier film's NAME (the same brief a second time, or a look
// test named like the last one) would silently get the old film's clips instead of rendering its own.
export async function staleScenes(abs: string, dir: string, total: number): Promise<number[]> {
  const out: number[] = [];
  for (const n of sceneFiles(dir)) if (n <= total && (await lastTakeVsLine(abs, dir, n)).same === false) out.push(n);
  return out;
}

function sceneFiles(dir: string): number[] {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).map((f) => /^scene-(\d+)\.mp4$/.exec(f)?.[1]).filter((x): x is string => !!x).map(Number).sort((a, b) => a - b);
}

function parseScenes(s: string | number[] | undefined): number[] {
  if (s === undefined) return [];
  const arr = Array.isArray(s) ? s : String(s).split(/[\s,]+/).map(Number);
  return arr.filter((n) => Number.isInteger(n) && n > 0);
}

// tqdm progress bars arrive as one line of \r-separated segments; keep the last segment of each.
function tailFile(file: string, lines: number, fromOffset = 0): string {
  if (!fs.existsSync(file)) return "";
  const buf = fs.readFileSync(file);
  return buf.subarray(fromOffset).toString("utf8").trim().split("\n")
    .map((l) => l.split("\r").filter((x) => x.trim()).pop() ?? "").slice(-lines).join("\n");
}

// Per-scene wall time from the mp4 mtimes: scene i took mtime(i) - max(mtime(i-1), launch).
function sceneTimings(dir: string, since: number): { scene: number; seconds: number }[] {
  const out: { scene: number; seconds: number }[] = [];
  let prev = since;
  for (const i of sceneFiles(dir)) {
    const m = fs.statSync(path.join(dir, `scene-${i}.mp4`)).mtimeMs;
    if (m >= since) out.push({ scene: i, seconds: Math.round((m - prev) / 1000) });
    prev = Math.max(prev, m);
  }
  return out;
}

// Contact sheets (skills/film/scripts/sheet.sh, six frames per scene, one row per scene) in groups
// small enough for a vision model, plus rig/precheck.py verdicts. CPU only, except the transcript
// (Parakeet on the GPU, a few seconds), which only the render tools ask for, while the model is unloaded.
// A sheet newer than all of its clips is reused, and precheck caches per scene, so review_scenes right
// after a render costs a second.
const MAX_TAKES = 3;
const MAX_IMAGES = 16;  // ds4-server: "too many images; at most 16 are allowed"
// Images per review call, sized from pi's own context estimate (2026-09-27). pi-ai caps a reply's output at
// contextWindow - estimate - 4096 and estimates every image at 1,200 tokens (ds4 spends at most 381). On 2026-09-26 a
// 13-image review at about 60K of context was left 1,673 output tokens, ended with no verdicts, and pi compacted and
// retried (the 2026-09-26 halloween portrait run). Keep at least MIN_REPLY tokens for the verdicts and ask
// for the rest in the next call.
const PI_IMAGE_TOKENS = 1200, PI_RESERVE = 4096, MIN_REPLY = 8000, REVIEW_BATCH = 8;
export function imagesThatFit(estimate: number | null | undefined, window: number | undefined, textTokens: number): number {
  const est = estimate ?? 40_000, win = window ?? 83_616;
  const n = Math.floor((win - est - textTokens - PI_RESERVE - MIN_REPLY) / PI_IMAGE_TOKENS);
  return Math.max(1, Math.min(REVIEW_BATCH, MAX_IMAGES, n));
}
function takesOf(dir: string, scene: number): number {
  if (!fs.existsSync(dir)) return 0;
  const redos = fs.readdirSync(dir).filter((d) => /^redo-\d+$/.test(d) && fs.existsSync(path.join(dir, d, `scene-${scene}.mp4`))).length;
  return redos + (fs.existsSync(path.join(dir, `scene-${scene}.mp4`)) ? 1 : 0);
}
async function sheetAndPrecheck(name: string, scenes: number[], portrait: boolean, signal?: AbortSignal, opts: { transcribe?: boolean; attach?: boolean; maxImages?: number } = {}) {
  const dir = path.join(VIDEOS, name);
  const per = portrait ? 4 : 6;
  const groups: number[][] = [];
  for (let i = 0; i < scenes.length; i += per) groups.push(scenes.slice(i, i + per));
  const sheets: string[] = [];
  for (const g of groups) {
    // The contact sheet is for the human (`open` it); the model gets one image per clip (below).
    const p = path.join(dir, `sheet-${g.join("-")}.png`);
    const newest = Math.max(...g.map((n) => { try { return fs.statSync(path.join(dir, `scene-${n}.mp4`)).mtimeMs; } catch { return Infinity; } }));
    if (!(fs.existsSync(p) && fs.statSync(p).mtimeMs > newest)) {
      const r = await run("zsh", [path.join(REPO, "skills/film/scripts/sheet.sh"), name, ...g.map(String)], { timeoutMs: 300_000, signal });
      const out = r.stdout.trim().split("\n").pop() ?? "";
      if (r.code !== 0 || !out.endsWith(".png")) { sheets.push(`sheet failed for scenes ${g.join(" ")}: ${r.stderr.trim()}`); continue; }
    }
    sheets.push(p);
  }
  // One labelled image per clip, its four frames in a 2x2 grid (rig/review_images.py; 2026-09-26, rig/bench/
  // review-bench.py): ds4 gives an image at most 381 tokens, so a 6-row sheet showed the model each frame at about
  // 200x112 px, one clip per image at about 500x290. ds4 takes at most 16 images per request.
  const images: ImagePart[] = [];
  let shown = opts.attach ? scenes.slice(0, opts.maxImages ?? MAX_IMAGES) : [];
  // Who spoke (rig/sync/whospoke.py, 2026-10-04): for a speaking shot with two or more faces that the sync gate passed,
  // whose line it is (the cast portrait) beside every face at the same moments of the line, the face that moved with the
  // voice framed in green. The gate only knows that one mouth moved with the voice: the iteration-9 film, shot 3, passed with
  // the minister speaking the king's line, and the director kept it. The render tools draw these while the model is
  // unloaded (CPU, about 20-40 s a shot); review_scenes attaches the cached ones, each right after its clip, inside the
  // same image budget. Any failure only leaves the picture out.
  const who = new Map<number, { png: string; speaker: string | null }>();
  const whoScenes = opts.attach ? shown : scenes;
  if (whoScenes.length) {
    const w = await run("python3", [path.join(REPO, "rig/sync/whospoke.py"), dir, ...whoScenes.map(String)], { timeoutMs: 1_200_000, signal });
    for (const l of w.stdout.split("\n")) {
      try { const r = JSON.parse(l); if (r?.png && fs.existsSync(r.png)) who.set(Number(r.scene), { png: r.png, speaker: r.speaker ?? null }); } catch { /* not a result line */ }
    }
  }
  if (opts.attach && shown.length) {
    const cap = opts.maxImages ?? MAX_IMAGES, fit: number[] = [];
    let used = 0;
    for (const n of shown) { const cost = who.has(n) ? 2 : 1; if (used + cost > cap) break; used += cost; fit.push(n); }
    if (!fit.length) { fit.push(shown[0]); who.delete(shown[0]); }
    shown = fit;
  }
  const whoShown: { scene: number; speaker: string | null }[] = [];
  // A scene with an earlier take is shown as previous-vs-new (review_images.py pairs), so a redo can be judged against
  // what it replaced; keep_take puts the previous one back (2026-09-27).
  const paired = shown.filter((n) => takesOf(dir, n) > 1);
  if (shown.length) {
    const g = await run("python3", [path.join(REPO, "rig/review_images.py"), "grids", dir, ...shown.filter((n) => !paired.includes(n)).map(String)], { timeoutMs: 600_000, signal });
    const pr = paired.length ? await run("python3", [path.join(REPO, "rig/review_images.py"), "pairs", dir, ...paired.map(String)], { timeoutMs: 600_000, signal }) : { stdout: "", stderr: "", code: 0 };
    const files = new Map<number, string>();
    for (const f of (g.stdout + "\n" + pr.stdout).trim().split("\n").filter((l) => l.endsWith(".png") && fs.existsSync(l))) {
      const m = /(?:clip|pair)-(\d+)\.png$/.exec(f); if (m) files.set(Number(m[1]), f);
    }
    let clipImages = 0;
    for (const n of shown) {
      const f = files.get(n); if (!f) continue;
      images.push({ type: "image", data: fs.readFileSync(f).toString("base64"), mimeType: "image/png" }); clipImages++;
      const ws = who.get(n);
      if (ws) { images.push({ type: "image", data: fs.readFileSync(ws.png).toString("base64"), mimeType: "image/png" }); whoShown.push({ scene: n, speaker: ws.speaker }); }
    }
    if (clipImages !== shown.length) sheets.push(`clip images failed (${clipImages} of ${shown.length}): ${(g.stderr + pr.stderr).trim().slice(-300)}`);
  }
  const jsonPath = path.join(dir, `precheck-${scenes.join("-") || "all"}.json`);
  const pcArgs = [path.join(REPO, "rig/precheck.py"), name, ...scenes.map(String), "--json", jsonPath, ...(opts.transcribe ? ["--transcribe"] : [])];
  const pc = await run("python3", pcArgs, { timeoutMs: 900_000, signal });
  const precheck = (pc.stdout.trim() || pc.stderr.trim()).split("\n").slice(-60).join("\n");
  return { sheets, images, shown, paired, who: whoShown, precheck, precheckJson: jsonPath };
}

const PRECHECK_LEGEND = "Pre-checks (rig/precheck.py, pixels and audio only): REDO = a pixel defect (uniform black bars, a frozen or black clip); redo that scene, never keep it as \"the look\". LOOK = a possible border or mask that dark night pictures also trigger: look at that clip yourself; redo it only if you see a drawn frame, a black circle or bars. OK = no pixel defect; the pre-check cannot see a wrong landmark, object or person: that is your job on the sheet. audio: what the transcript heard next to the line the scene asked for. sync N: the dialogue-sync gate's verdict for that shot (PASS, FAIL or UNMEASURABLE; you cannot see sync on stills, so act on this line). PASS means one face moved in sync with the voice, not that it was the right face: on the sheet, the open mouth must be the named speaker's and every other mouth closed, or redo the shot with the speaker named before the verb (the iteration-9 film, shot 3, passed with the minister speaking the king's line).";

// The scene texts travel with the film (story.sh copies project.txt into the folder).
function sceneTexts(name: string): string[] {
  const p = path.join(VIDEOS, name, "project.txt");
  if (!fs.existsSync(p)) return [];
  return sceneLines(fs.readFileSync(p, "utf8")).map((l) => l.slice(1, -1).replace(/^(\[[^\]]*\] )+/, ""));
}

// What each clip ASKED for, next to the images, so the model compares text against image clip by clip. Added after
// the first hands-off film (2026-09-23): DeepSeek Vision judged pixels well but let a Giza pyramid pass for "the
// Transamerica Pyramid" and Big Ben for "Coit Tower". The full line since 2026-09-26 (it was cut at 260 characters,
// which hid the props and people at the end of most lines).
export function describeClips(name: string, scenes: number[], shown: number[], paired: number[] = [], who: { scene: number; speaker: string | null }[] = []) {
  const texts = sceneTexts(name);
  const dir = path.join(VIDEOS, name);
  const rows = shown.map((s) => `clip ${s} (take ${takesOf(dir, s)} of at most ${MAX_TAKES}): ${texts[s - 1] ?? "(no text)"}`);
  const rest = scenes.filter((s) => !shown.includes(s));
  const whoAt = new Set(who.map((w) => w.scene));
  const order = shown.flatMap((s) => (whoAt.has(s) ? [`clip ${s}`, `who-spoke ${s}`] : [`clip ${s}`]));
  return (who.length
    ? `The ${order.length} images are in this order: ${order.join(", ")}. Each clip image shows four frames spread evenly over the clip, left to right then top to bottom, with its clip number written at the top. Each who-spoke image follows its clip: on the left, whose line it is (their cast portrait when they have one); on the right, one strip per face at the same moments of the line, with the face whose mouth moved with the voice framed in green. The sync gate only knows that one mouth moved with the voice, not whose. In that clip's verdict add "who: <name> yes" when the green face is that person, or "who: no, it is <who>". A no is a redo: name the speaker right before the verb and write everyone else silent, mouth closed.`
    : `The ${shown.length} images are one per clip, in this order: ${shown.map((s) => `clip ${s}`).join(", ")}. Each shows four frames spread evenly over the clip, left to right then top to bottom, with its clip number written at the top.`) +
    (paired.length ? ` Clips ${paired.join(" ")} were redone: their image shows the PREVIOUS take in the top row and the NEW take in the bottom row, at the same moments. Say which take is better for each; if the previous one is better, call keep_take for that clip.` : "") +
    (rest.length ? ` Clips ${rest.join(" ")} are not in this call, so that your reply has room for the verdicts: write the verdicts for these ${shown.length} first, then call review_scenes for ${rest.join(" ")}.` : "") +
    `\nWhat each clip was asked to show:\n${rows.join("\n")}\n` +
    `Write one line per clip now, while the images are in front of you (they are removed from your context after this reply): "clip N: asked ... / shows ... / keep or redo". Be strict: the named place, landmark, reference or object must be the one asked for, not a look-alike (a Giza pyramid is not the Transamerica Pyramid, a clock tower is not Coit Tower, a plain hallway is not the red-carpeted hotel corridor of the reference), with nothing extra the words summoned (a van named for scale, a saxophone named as a sound); the scene opens on its own first sentence (no prologue, border, mask); photoreal; the named people once each, in the asked makeup and costume; the beat and the blocking visible; a speaking character faces the camera with the mouth visible, and the open mouth is the named speaker's while every other mouth in frame stays closed (the sync gate cannot tell who spoke). Then compare the clips of each recurring character by FACE and HAIR (colour, length, face shape, age), not only by costume and makeup, and name the drifting clips. A REDO pre-check verdict is a redo.`;
}

// ---------- shared state and guards ----------

let activeRender: { name: string; kind: string; started: number } | null = null;

async function refuseIfRendering(what: string) {
  const procs = await renderProcs();
  if (activeRender || procs.any) {
    throw new Error(`${what} refused: a render is in progress (${activeRender ? `${activeRender.kind} ${activeRender.name} since ${new Date(activeRender.started).toLocaleTimeString()}` : `processes ${JSON.stringify(procs)}`}). Wait for it; never start a second one.`);
  }
}

// Hold an LLM call while a render process exists (a render started outside these tools, or one that
// outlived an aborted tool call). Polls every 20 s, forever if need be: prompting during a render is
// the one thing this rig must never do.
async function holdWhileRendering(ctx: ExtensionContext, where: string) {
  if (process.env.FILM_RIG_UNIT_TEST === "1") return;   // rig/tests/run.sh unit only: the suite must run beside a render
  let held = 0;
  while (!ctx.signal?.aborted) {
    const procs = await renderProcs();
    if (!procs.any) break;
    if (held % 3 === 0 && ctx.hasUI) ctx.ui.notify(`film-rig: holding the model call (${where}) while a render runs: engine ${procs.engine.length}, runners ${procs.runners.length}`, "warning");
    held++;
    await sleep(20_000, ctx.signal);
  }
  if (held) ctx.ui.notify(`film-rig: render finished; continuing after ${held * 20} s`, "info");
}

// ---------- the Mac's GPU hold (2026-10-04, ~/repos/local-rig/docs/hold.md) ----------
// One lock for the GPU, kept by the hold gate in front of llama-swap (:8090). The render tools take it BEFORE they
// unload the model. From that moment every pi session waits (local-rig's hold.ts) and every other client is refused,
// so nobody can reload the model in the gap between the unload and the render: until 2026-10-04 the context hook
// below only held calls once a render process existed, and a busy session could reload qwen38 in that gap and stall
// the film. The hold lasts through the post-render checks (they transcribe on the GPU) and ends when the tool
// returns; a second render or an m3d job queues for it instead of being refused. With no gate (not installed, or
// down) the tools fall back to the old rule: unload, settle, refuse while a render runs.
interface GpuHold { id: string }

async function gateCall(pathq: string, body?: unknown, timeoutMs = 10_000, signal?: AbortSignal): Promise<any | null> {
  const t = AbortSignal.timeout(timeoutMs);
  try {
    const res = await fetch(`${SWAP}${pathq}`, {
      method: body === undefined ? "GET" : "POST",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: signal ? AbortSignal.any([signal, t]) : t,
    });
    if (res.status === 404) return null; // llama-swap itself answers :8090: no gate installed
    const j = await res.json().catch(() => null);
    if (!res.ok) throw new Error(`hold gate: ${j?.error?.message ?? res.status}`);
    return j;
  } catch (e) {
    if (signal?.aborted) throw e;
    if (e instanceof Error && e.message.startsWith("hold gate:")) throw e;
    return null; // nothing answers, or it answered garbage: treat as no gate
  }
}

async function takeGpuHold(kind: string, reason: string, say: (s: string) => void, signal?: AbortSignal): Promise<GpuHold | null> {
  // FILM_RIG_MODE=resident keeps the director's small model loaded beside a 480p render: the gate still closes and
  // drains, but does not unload it (nothing may prompt it until the render ends, which the blocking tool guarantees)
  const v = await gateCall("/hold/acquire", { kind, reason, owner: `film-rig (pi ${process.pid})`, pids: [process.pid], parent: process.env.HOLD_ID ?? "", keep_loaded: mode() === "resident" }, 30_000, signal);
  if (!v?.id) return null;
  let last = "";
  for (let s = v; ;) {
    if (s.state === "granted") {
      if (last) say(`GPU hold ${v.id} granted`);
      return { id: v.id };
    }
    if (s.state === "gone") throw new Error(`GPU hold ${v.id} ended before it was granted (hold status shows why)`);
    const msg = s.position > 0 ? `waiting for the GPU: ${s.position} job(s) ahead; it is ${s.why}`
      : s.unloading ? `unloading ${(s.running ?? []).join(", ")} for this render`
      : s.in_flight > 0 ? `waiting for ${s.in_flight} model call(s) from other sessions to finish (new ones wait now)`
      : `waiting for the GPU (${s.why})`;
    if (msg !== last) { say(msg); last = msg; }
    if (signal?.aborted) {
      await releaseGpuHold({ id: v.id }, "the tool call was aborted while it waited");
      throw new Error("aborted while waiting for the GPU");
    }
    try {
      s = await gateCall(`/hold/wait?timeout=20&id=${encodeURIComponent(v.id)}`, undefined, 40_000, signal);
    } catch (e) {
      if (signal?.aborted) await releaseGpuHold({ id: v.id }, "the tool call was aborted while it waited");
      throw e;
    }
    if (!s) throw new Error("the hold gate stopped answering while this tool waited for the GPU; try again");
  }
}

async function attachGpuHold(h: GpuHold | null, pid?: number) {
  if (h && pid) await gateCall("/hold/attach", { id: h.id, pids: [pid] }).catch(() => undefined);
}

async function releaseGpuHold(h: GpuHold | null, why: string) {
  if (h) await gateCall("/hold/release", { id: h.id, why }).catch(() => undefined);
}

// bin/still and mflux (the image model, about 46 GB) run only inside a render, from story.sh's [still]: beside the
// loaded director model they would not fit in memory (2026-09-26).
const BLOCKED_BASH = /\b(vidgen|story\.sh|run-queue\.sh|redo\.sh|ltx-2-mlx|ds4-server|llama-server|ds4-serve|llama-swap|launchctl|pkill|killall|kill\s|nohup|8090\/(unload|v1|api)|bin\/still|mflux-[\w-]+)\b/;
// Paths into the film output folder (~/Videos/vidgen/...) are blanked before matching, so `ls`, `open`,
// `ffprobe` and `afplay` on a film work; only the command words start renders. On 2026-09-24 the bare
// `vidgen` match blocked five such calls, including `open` of the look-test sheet and the finish sound
// the human asked for, and the compaction summary carried "open is blocked" forward as a lesson.
const FILM_PATH = /["']?[~\w./$-]*Videos\/vidgen\b[\w./-]*["']?/g;
// [s]tory.sh, "vid"gen and v\idgen are the same words to the shell, so glob brackets, quotes and backslashes go before
// the match (2026-10-04: after `grep ... stories/story.sh` was blocked, the qwen38 director ran it as stories/[s]tory.sh).
export function bashBlocked(cmd: string): boolean {
  return BLOCKED_BASH.test(cmd.replace(/[\[\]"'\\]/g, "").replace(FILM_PATH, "FILM_PATH"));
}
// The list above is the director's (2026-10-04: before, film-rig blocked `kill`, `nohup`, `launchctl` and vidgen in
// EVERY pi session, film or not). Every session, director or not, keeps this narrower rule: an agent never runs,
// kills or restarts a model server or the hold gate, and never starts or ends a GPU hold by hand. A ds4-server,
// llama-server or ds4-serve started by hand loads a model outside llama-swap, past the hold (the user's rule:
// nothing forces the LLM back on while it is held on purpose); a SIGKILL on one leaks its wired Metal memory until
// reboot; `hold off` would end someone's deliberate hold, and `hold on` from an agent holds its own model off with
// nobody to release it. GPU jobs go through `hold run -- <cmd>`. Reading their logs and files stays allowed.
const MODEL_SERVER_BASH = /(?:^|[;&|(]\s*|\b(?:sudo|nohup|exec|env|time)\s+)(?:\S*\/)?(?:ds4-server|llama-server|ds4-serve|llama-swap)\b|\b(?:pkill|killall)\b[^;&|]*\b(?:ds4-server|llama-server|llama-swap|hold)\b|\blaunchctl\b[^;&|]*\b(?:llama-swap|hold-gate)\b|(?:^|[;&|(]\s*)(?:\S*\/)?hold\s+(?:on|off|release)\b/;
export function bashBlockedEverywhere(cmd: string): boolean {
  return MODEL_SERVER_BASH.test(cmd.replace(/[\[\]"'\\]/g, ""));
}

// ---------- context shaping (2026-09-24) ----------
// Two changes to what a local model is sent, both measured on the nyc-2000-slavic-neon run
// (the 2026-09-24 post-mortem):
// 1. Images are shown once. A contact sheet stays in the context until the model has replied to it, then it
//    becomes a one-line note. ds4-server skips its disk KV cache for any request that carries an image, and
//    re-reads an image-bearing request from token 0 when its live cache mismatches at the model's own first
//    generated token. With sheets kept, every wake re-read the whole context twice: about 21 min of a 114 min
//    run. Text-only requests hit both caches.
// 2. Reasoning older than the latest compaction is dropped. A hands-off film is one user turn, so pi re-sends
//    every earlier thinking block; after compaction 2 the kept messages still held 97.6K characters of stale
//    deliberation. The request after a compaction re-reads everything anyway, so stripping there costs no cache
//    hit, and every reply after the compaction keeps its thinking.
const SHOWN_ONCE = "[contact sheet image: shown to you once and then removed from the context so the model server keeps its cache; call review_scenes again to see it]";
// 3. llama-swap's loading banner is taken out of the replayed reasoning (2026-09-26). With sendLoadingState: true,
//    llama-swap streams "━━━━━\nllama-swap loading model: vision-q4 ... Done! (23.36s)\n━━━━━\n \n" as reasoning while
//    it loads the model; pi stores it as the model's thinking and replays it in every later request. The model never
//    generated those bytes, so the replayed history stops matching the server's cache at that reply: in the
//    halloween run every sheet review (the request after each wake) was re-read from token 0, 42-54K tokens, and in
//    the loop test a text request fell back to an older disk checkpoint. Stripping it restores the exact reasoning.
const SWAP_BANNER = /^━━━━━\nllama-swap loading model:[^\n]*\n[\s\S]*?\n━━━━━\n(?: \n)?/;
export const stripSwapBanner = (t: string) => t.replace(SWAP_BANNER, "");
const tsOf = (t: unknown) => (typeof t === "number" ? t : typeof t === "string" ? Date.parse(t) : NaN);
export function shapeContext(messages: any[], opts: { imagesOnce?: boolean } = {}): { messages: any[]; images: number; thinking: number; banners: number } {
  const imagesOnce = opts.imagesOnce ?? true; // the director's rule; other sessions keep their images (2026-10-04)
  let lastAssistant = -1;
  for (let i = messages.length - 1; i >= 0; i--) if (messages[i]?.role === "assistant") { lastAssistant = i; break; }
  let compactedAt = -Infinity;
  for (const m of messages) if (m?.role === "compactionSummary") compactedAt = Math.max(compactedAt, tsOf(m.timestamp) || -Infinity);
  let images = 0, thinking = 0, banners = 0;
  messages.forEach((m, i) => {
    if (!m || !Array.isArray(m.content)) return;
    // FILM_RIG_KEEP_SWAP_BANNER=1 keeps it, only to reproduce the cache miss in a test (rig/tests/loop.py)
    if (process.env.FILM_RIG_KEEP_SWAP_BANNER !== "1" && m.role === "assistant" && m.content.some((c: any) => c?.type === "thinking" && typeof c.thinking === "string" && SWAP_BANNER.test(c.thinking))) {
      m.content = m.content.map((c: any) => (c?.type === "thinking" && typeof c.thinking === "string" && SWAP_BANNER.test(c.thinking) ? (banners++, { ...c, thinking: stripSwapBanner(c.thinking) }) : c));
    }
    if (imagesOnce && m.role === "toolResult" && i < lastAssistant && m.content.some((c: any) => c?.type === "image")) {
      m.content = m.content.map((c: any) => (c?.type === "image" ? (images++, { type: "text", text: SHOWN_ONCE }) : c));
    }
    if (m.role === "assistant" && tsOf(m.timestamp) < compactedAt && m.content.some((c: any) => c?.type === "thinking")) {
      const kept = m.content.filter((c: any) => c?.type !== "thinking");
      thinking += m.content.length - kept.length;
      m.content = kept.length ? kept : [{ type: "text", text: "(reasoning from before the last compaction omitted)" }];
    }
  });
  return { messages, images, thinking, banners };
}

// /skill:studio and /skill:film turn director mode on by themselves: on 2026-09-24 studio ran without it, so the
// landmark and writing rules lived only in files read once and were compacted away before the plan was written.
export const isFilmSkillPrompt = (p?: string) => !!p && (/^\s*\/skill:(studio|film)\b/.test(p) || /<skill name="(studio|film)"/.test(p));

// ---------- the extension ----------

export default function filmRig(pi: ExtensionAPI) {
  const readModel = (m: unknown): ActiveModel | undefined => {
    const x = m as { provider?: string; id?: string; input?: string[] } | undefined;
    return x?.provider && x?.id ? { provider: x.provider, id: x.id, input: x.input } : undefined;
  };
  pi.on("session_start", async (_e, ctx) => {
    activeModel = readModel(ctx.model);
    // Restore /film state from the session so `pi -c` resumes in director mode.
    try {
      for (const e of ctx.sessionManager.getEntries() as { type?: string; customType?: string; data?: { director?: boolean } }[]) {
        if (e.type === "custom" && e.customType === "film-rig" && typeof e.data?.director === "boolean") director = e.data.director;
      }
    } catch { /* no entries yet */ }
    if (ctx.hasUI) ctx.ui.notify(`film-rig: mode=${mode()}, lifecycle=${lifecycle()}, director=${director ? "on" : "off (type /film)"}, model=${activeModel ? activeModel.provider + "/" + activeModel.id : "?"}${modelSeesImages() ? "" : " (cannot see images)"}`, "info");
  });
  pi.on("model_select", async (e, ctx) => { activeModel = readModel((e as { model?: unknown }).model) ?? readModel(ctx.model) ?? activeModel; });
  pi.on("before_agent_start", async (event, ctx) => {
    await holdWhileRendering(ctx, "before_agent_start");
    if (!director && isFilmSkillPrompt((event as { prompt?: string }).prompt)) {
      director = true;
      pi.appendEntry("film-rig", { director: true, via: "skill", model: activeModel ? `${activeModel.provider}/${activeModel.id}` : undefined });
      if (ctx.hasUI) ctx.ui.notify("film-rig: director mode ON for the film skill (its rules sit in the system prompt, where compaction cannot drop them)", "info");
    }
    directorPrompt_seen = event.systemPrompt.includes(DIRECTOR_MARKER); // the current prompt, so /film off ends it
    if (director && !event.systemPrompt.includes(DIRECTOR_MARKER)) {
      return { systemPrompt: `${event.systemPrompt}\n\n# Film director mode (/film)\n\n${directorPrompt()}` };
    }
  });
  let strippedThinking = 0;
  pi.on("context", async (event, ctx) => {
    await holdWhileRendering(ctx, "context");
    const msgs = (event as { messages?: any[] }).messages;
    if (!Array.isArray(msgs)) return;
    const shaped = shapeContext(msgs, { imagesOnce: isDirector() });
    if (shaped.thinking > strippedThinking && ctx.hasUI) ctx.ui.notify(`film-rig: ${shaped.thinking} reasoning blocks from before the last compaction left out of the context`, "info");
    strippedThinking = shaped.thinking;
    if (shaped.images || shaped.thinking || shaped.banners) return { messages: shaped.messages };
  });
  pi.on("session_before_compact", async (_e, ctx) => {
    const procs = await renderProcs();
    if (activeRender || procs.any) {
      if (ctx.hasUI) ctx.ui.notify("film-rig: compaction cancelled while a render runs", "warning");
      return { cancel: true };
    }
  });
  pi.on("tool_call", async (event) => {
    if (event.toolName !== "bash") return;
    const cmd = String((event.input as { command?: string }).command ?? "");
    if (!isDirector()) {
      if (bashBlockedEverywhere(cmd)) {
        return { block: true, reason: "blocked (film-rig, every session): agents never run, kill or restart a model server (ds4-server, llama-server, ds4-serve, llama-swap) or the hold gate, and never start or end a GPU hold by hand. llama-swap loads models on demand through :8090, and the hold gate decides when. Run a GPU job with `hold run -- <cmd>`; `hold status` shows who holds the GPU. Logs and files are fine to read." };
      }
      return;
    }
    if (bashBlocked(cmd)) {
      return { block: true, reason: "film-rig: blocked. Renders go through render_and_wait / redo_scenes (they preflight, unload the model and wait); model servers, launchctl and kill are off limits to the agent. To read a script, skill or log whose name is one of these, use the read tool: bash is blocked on these names even when it only reads. Contact sheets: review_scenes." };
    }
  });

  pi.registerCommand("rig", {
    description: "film-rig preflight: render processes, model servers, wired memory, queue tail",
    handler: async (_args, ctx) => { ctx.ui.notify(JSON.stringify(await preflight(), null, 1), "info"); },
  });

  // /film [brief] | /film off | /film status — director mode with the session's current model.
  pi.registerCommand("film", {
    description: "Film director mode with this session's model: /film <brief> starts a film, /film off leaves the mode, /film status shows the GPU preflight",
    getArgumentCompletions: (prefix) => ["off", "status"].filter((s) => s.startsWith(prefix)).map((value) => ({ value, label: value })),
    handler: async (args, ctx) => {
      const a = (args ?? "").trim();
      activeModel = readModel(ctx.model) ?? activeModel;
      if (a === "status") { ctx.ui.notify(JSON.stringify(await preflight(), null, 1), "info"); return; }
      if (a === "off") { director = false; pi.appendEntry("film-rig", { director: false }); ctx.ui.notify("film-rig: director mode off", "info"); return; }
      director = true;
      pi.appendEntry("film-rig", { director: true, model: activeModel ? `${activeModel.provider}/${activeModel.id}` : undefined });
      if (!fs.existsSync(DIRECTOR_MD)) ctx.ui.notify(`film-rig: ${DIRECTOR_MD} is missing; the model will only have the film skill`, "warning");
      if (!modelSeesImages()) ctx.ui.notify(`film-rig: ${activeModel?.provider}/${activeModel?.id} cannot see images, so it cannot review contact sheets. Switch with /model to local/vision-q4-400k, local/vision-500k or local/qwen27-262k (or start one with \`model\` and pick it).`, "warning");
      ctx.ui.notify(`film-rig: director mode ON with ${activeModel ? activeModel.provider + "/" + activeModel.id : "the current model"}; renders ${mode() === "resident" ? "keep the model resident" : lifecycle() === "swap" ? "unload it via llama-swap and reload on the next reply" : "stop it with `model stop` and restart it after"}. ${a ? "Sending your brief." : "Describe the film you want; the director will interview you once."}`, "info");
      if (a) pi.sendUserMessage(a);
    },
  });

  // Common tail: wait for a detached render to finish, then report.
  async function waitAndReport(opts: {
    name: string; dir: string; portrait: boolean; kind: string; launchedAt: number; queueOffset: number;
    doneRegex: RegExp; child?: ReturnType<typeof spawn>; sheetScenes?: number[]; totalScenes: number;
    onUpdate?: (r: { content: TextPart[] }) => void; signal?: AbortSignal; pre: unknown; settle: unknown;
  }) {
    const { name, dir } = opts;
    let status = "TIMEOUT";
    let childExited = false;
    opts.child?.on("exit", () => { childExited = true; });
    const t0 = Date.now();
    while (Date.now() - t0 < MAX_WAIT_MS) {
      if (opts.signal?.aborted) { status = "ABORTED (the render continues in the background; call the tool again to wait for it)"; break; }
      const m = opts.doneRegex.exec(tailFile(QUEUE_LOG, 200, opts.queueOffset));
      if (m) { status = m[1]; break; }
      if (childExited) {
        const procs = await renderProcs();
        if (!procs.any) { status = fs.existsSync(path.join(dir, `${name}.mp4`)) && fs.statSync(path.join(dir, `${name}.mp4`)).mtimeMs > opts.launchedAt ? "OK" : "FAILED"; break; }
      }
      const done = sceneFiles(dir).length;
      const el = Math.round((Date.now() - opts.launchedAt) / 1000);
      opts.onUpdate?.({ content: [{ type: "text", text: `${opts.kind} ${name}: ${done}/${opts.totalScenes} scenes on disk, ${Math.floor(el / 60)}m${el % 60}s elapsed. Last: ${tailFile(path.join(REPO, `logs/story-${name}.log`), 1)}` }] });
      await sleep(POLL_MS, opts.signal);
    }
    // let run-queue.sh / story.sh / redo.sh exit (they write the log line just before they end), so the
    // context guard does not hold the next model call for a runner that is already finishing
    for (let i = 0; i < 15 && (await renderProcs()).any; i++) await sleep(1000, opts.signal);
    activeRender = null;
    // redo.sh has no queue line: a refused stitch shows as "NOT STITCHED ... sync gate" in the story log (2026-09-27)
    if (status === "FAILED" && /NOT STITCHED [^\n]*sync gate/.test(tailFile(path.join(REPO, `logs/story-${name}.log`), 40))) status = "SYNCGATE";
    const syncLines = latestSyncLines(tailFile(path.join(REPO, `logs/story-${name}.log`), 400));
    const timings = sceneTimings(dir, opts.launchedAt);
    const rendered = timings.map((t) => t.scene);
    const sheetScenes = opts.sheetScenes?.length ? opts.sheetScenes : rendered.length ? rendered : sceneFiles(dir).slice(-3);
    // The transcript uses the GPU for a few seconds: only here, while the language model is unloaded.
    const review = status.startsWith("ABORTED") ? null : await sheetAndPrecheck(name, sheetScenes, opts.portrait, opts.signal, { transcribe: mode() === "alternate" });
    const total = Math.round((Date.now() - opts.launchedAt) / 1000);
    const restartNote = await restartEngineIfNeeded((s) => opts.onUpdate?.({ content: [{ type: "text", text: s }] }));
    const onDisk = sceneFiles(dir);
    const missing = Array.from({ length: opts.totalScenes }, (_, i) => i + 1).filter((n) => !onDisk.includes(n));
    const lines = [
      `${opts.kind} ${name}: ${status} after ${Math.floor(total / 60)}m${total % 60}s. Scenes on disk: ${onDisk.length}/${opts.totalScenes}${missing.length ? ` (missing: ${missing.join(" ")})` : ""}.`,
      status === "PAUSED" ? `Paused cleanly before the next scene (stop-after). Review the sheet; call render_and_wait again on the same project to continue (finished scenes are skipped), or fix the project first.` : "",
      status === "FAILED" ? `FAILED: read the story-log tail below; a Metal OOM means something else was on the GPU; fix and call render_and_wait again (finished scenes are skipped).` : "",
      status === "SYNCGATE" ? `NOT STITCHED, by the dialogue-sync gate: every scene is rendered, but the dialogue shots marked FAIL or UNMEASURABLE below are not in sync (the rig already tried ${process.env.SYNC_TRIES ?? 3} takes of each). For each one, either (a) redo_scenes after changing the line: the speaker's face in view and unobstructed through the line (any framing from close-up to full length, frontal to three-quarter), anyone else in the frame silent with a closed mouth, no gesture or walking while speaking, a beat before the words; or (b) make the line off-screen: put [offscreen] at the start of the scene line and rewrite the shot so the speaker is turned away or out of frame (a listener's reaction, a wide), keeping the words; or (c) if you must keep the take, keep_take with accept_sync_fail "<why>" (it goes into the film's report). Never call a shot in sync unless its sync line says PASS.` : "",
      syncLines.length ? `Dialogue-sync gate (rig/sync/gate.py, meter ${/METER_VERSION = "([^"]+)"/.exec(fs.readFileSync(path.join(REPO, "rig/sync/syncmeter.py"), "utf8"))?.[1] ?? "?"}; you cannot judge lip sync from stills, so act on these lines):\n${syncLines.join("\n")}` : "",
      opts.kind === "redo" && missing.length ? `Only the named scenes were rendered; the film is not complete: call render_and_wait on the same project to render the missing scenes.` : "",
      timings.length ? `Per-scene wall time (s): ${timings.map((t) => `${t.scene}:${t.seconds}`).join(" ")}` : "No new scene was rendered in this call.",
      `Film: ${path.join(dir, name + ".mp4")}${fs.existsSync(path.join(dir, name + ".mp4")) ? "" : " (not stitched yet)"}`,
      review ? `${PRECHECK_LEGEND}\n${review.precheck}\nFull JSON: ${review.precheckJson}` : "",
      review ? `Contact sheets saved: ${review.sheets.join(", ")}. They are NOT attached here: an image in the first reply after a render makes the model server re-read your whole context from token 0. Next, call review_scenes with name "${name}" and scenes "${sheetScenes.join(" ")}" to look at them.` : "",
      `Story log tail:\n${tailFile(path.join(REPO, `logs/story-${name}.log`), 12)}`,
      `Settle before launch: ${JSON.stringify(opts.settle)}`,
      restartNote || `The model was ${mode() === "alternate" ? "unloaded for the render and reloads on this reply" : "kept resident (mode=resident)"}.`,
    ].filter(Boolean);
    const content: (TextPart | ImagePart)[] = [{ type: "text", text: lines.join("\n\n") }];
    return { content, details: { status, timings, missing, sheets: review?.sheets ?? [], precheck: review?.precheckJson ?? null, pre: opts.pre, settle: opts.settle } };
  }

  pi.registerTool({
    name: "render_and_wait",
    label: "Render and wait",
    description:
      "Render a film project (stories/projects/NN-<slug>.txt) scene by scene, unattended, and BLOCK until it finishes. Does the GPU preflight, unloads the local model first (the model is reloaded automatically on the next reply), launches stories/run-queue.sh detached, waits for OK|FAILED|PAUSED in logs/queue.log, then returns per-scene timings, the story-log tail and rig/precheck.py verdicts with the audio transcript, as text only (call review_scenes next for the contact sheets). Finished scenes are skipped, so calling it again on the same project resumes. until_scene=N pauses cleanly after scene N (for the early review of scenes 1-3); call again without it to continue. A 15 s scene takes about 2.5 min at 480p and 9 min at 720p in fast mode, about three times that with MODE=--quality; that wait is normal.",
    promptSnippet: "render_and_wait — render a project file unattended and wait for it (returns timings and pre-checks; then call review_scenes for the sheets)",
    promptGuidelines: [
      "Use render_and_wait for every render; never start vidgen, story.sh or run-queue.sh from bash.",
      "Call render_and_wait with until_scene=3 first, then review_scenes to look at the sheet, then render_and_wait again to finish.",
    ],
    parameters: Type.Object({
      project: Type.String({ description: "Project file path, e.g. stories/projects/13-my-film.txt" }),
      until_scene: Type.Optional(Type.Integer({ description: "Pause cleanly after this scene (e.g. 3 for the early check)" })),
      sheet: Type.Optional(Type.String({ description: "Scenes to put on the contact sheet, e.g. \"1 2 3\" (default: the scenes rendered in this call)" })),
    }),
    executionMode: "sequential",
    async execute(_id, params, signal, onUpdate) {
      if (activeRender) await refuseIfRendering("render_and_wait"); // this session's own render still runs (an aborted wait)
      const proj = resolveProject(params.project);
      await checkSyntax(proj.abs);
      await lintDialogue(proj.abs);
      if (!proj.scenes) throw new Error(`${proj.abs}: no scenes found (each scene is one double-quoted line inside SCENES=( ... ))`);
      const stale = await staleScenes(proj.abs, proj.dir, proj.scenes);
      if (stale.length) {
        throw new Error(`${proj.dir} already holds clips rendered from other lines than ${path.basename(proj.abs)} asks for (scene${stale.length > 1 ? "s" : ""} ${stale.join(" ")}: a different line, seed or mode). The render would skip them and keep those old clips. If this is a new film or look test, give it a new NAME= (for example ${proj.name}-2) and call render_and_wait again. If you edited lines of scenes already rendered in THIS film, use redo_scenes for them.`);
      }
      const finalMp4 = path.join(proj.dir, `${proj.name}.mp4`);
      if (fs.existsSync(finalMp4) && !params.until_scene && sceneFiles(proj.dir).length >= proj.scenes) {
        throw new Error(`${proj.name} is already finished (${finalMp4}). Use review_scenes to look at it or redo_scenes to re-render scenes.`);
      }
      const say = (s: string) => onUpdate?.({ content: [{ type: "text", text: s }] });
      const hold = await takeGpuHold("render", proj.name, say, signal);
      if (!hold) await refuseIfRendering("render_and_wait"); // no gate: one render at a time, as before 2026-10-04
      try {
        const pre = await preflight();
        say(`preflight ok; ${mode() === "alternate" ? "unloading the model and " : ""}waiting for memory to settle`);
        const settle = await unloadAndSettle(say, signal);
        if (!settle.ok) throw new Error(`GPU not clear after ${settle.seconds} s: ${JSON.stringify(settle)}. Something is still loaded; do not render. Pre-check: ${JSON.stringify(pre)}`);
        fs.mkdirSync(proj.dir, { recursive: true });
        const stopFile = path.join(proj.dir, "stop-after");
        if (params.until_scene) fs.writeFileSync(stopFile, String(params.until_scene) + "\n"); else if (fs.existsSync(stopFile)) fs.unlinkSync(stopFile);
        const queueOffset = fs.existsSync(QUEUE_LOG) ? fs.statSync(QUEUE_LOG).size : 0;
        const launchedAt = Date.now();
        // HOLD_ID: run-queue.sh and everything under it (story.sh, still, vidgen) render inside this tool's hold
        const child = spawn("zsh", [path.join(REPO, "stories/run-queue.sh"), proj.abs], { cwd: REPO, detached: true, stdio: "ignore", env: hold ? { ...process.env, HOLD_ID: hold.id } : process.env });
        child.unref();
        await attachGpuHold(hold, child.pid); // if this pi dies mid-render, the hold lives on with the render
        activeRender = { name: proj.name, kind: "render", started: launchedAt };
        const doneRegex = new RegExp(`^\\d\\d:\\d\\d (OK|FAILED|PAUSED|SYNCGATE) ${proj.name}\\b`, "m");
        return await waitAndReport({ name: proj.name, dir: proj.dir, portrait: proj.portrait, kind: "render", launchedAt, queueOffset, doneRegex, child, sheetScenes: parseScenes(params.sheet), totalScenes: proj.scenes, onUpdate, signal, pre, settle });
      } finally {
        // after an aborted wait the render goes on: the gate still sees it as a GPU job, so the LLM stays off until it ends
        await releaseGpuHold(hold, `render_and_wait ${proj.name} returned`);
      }
    },
  });

  pi.registerTool({
    name: "review_scenes",
    label: "Review scenes",
    description: "One image per named scene of a film (its four frames in a 2x2 grid, the clip number written on it; at most 16 per call) plus rig/precheck.py verdicts (REDO for black bars, masks, frozen or black clips; LOOK for softer flags) and the audio transcript next to each scene's quoted line. CPU only, no render. Call it right after every render_and_wait or redo_scenes (their results carry no images), and write your asked/shows verdict for every clip in that same reply: the images are shown once.",
    promptSnippet: "review_scenes — contact sheet and pre-checks for scenes of a film, no render",
    parameters: Type.Object({
      name: Type.String({ description: "Film NAME (its folder in ~/Videos/vidgen)" }),
      scenes: Type.String({ description: "Space-separated scene numbers, e.g. \"1 2 3\"; \"all\" for every scene" }),
    }),
    executionMode: "sequential",
    async execute(_id, params, signal, _onUpdate, ctx) {
      await refuseIfRendering("review_scenes");
      const dir = path.join(VIDEOS, params.name);
      if (!fs.existsSync(dir)) throw new Error(`no film folder ${dir}`);
      const all = sceneFiles(dir);
      const scenes = params.scenes.trim() === "all" ? all : parseScenes(params.scenes).filter((s) => all.includes(s));
      if (!scenes.length) throw new Error(`no such scenes; on disk: ${all.join(" ")}`);
      const portrait = /PORTRAIT=1\b/.test(fs.existsSync(path.join(dir, "project.txt")) ? fs.readFileSync(path.join(dir, "project.txt"), "utf8") : "");
      const usage = ctx?.getContextUsage?.();
      const maxImages = imagesThatFit(usage?.tokens, usage?.contextWindow, 1500 + 120 * scenes.length);
      const review = await sheetAndPrecheck(params.name, scenes, portrait, signal, { attach: true, maxImages });
      const text = [`${params.name}: scenes ${scenes.join(" ")} of ${all.length} on disk.`, `${PRECHECK_LEGEND}\n${review.precheck}`, `Contact sheets for the user (open them with \`open\`; you get one image per clip below): ${review.sheets.join(", ")}`, describeClips(params.name, scenes, review.shown, review.paired, review.who)].join("\n\n");
      return { content: [{ type: "text", text }, ...review.images], details: { sheets: review.sheets, precheck: review.precheckJson } };
    },
  });

  pi.registerTool({
    name: "redo_scenes",
    label: "Redo scenes",
    description: "Re-render ONLY the named scenes of a film with stories/redo.sh (old takes are kept in redo-N/; the other scenes are never rendered, even on a paused film) and BLOCK until done, then return timings and pre-checks; call review_scenes next for the sheet. Same text and same seed reproduce the same clip, so the tool refuses a scene whose text and seed are unchanged since its last take: edit the scene text (describe the missed landmark or object physically), add a [seed=N] token, or add [quality] (the slower dev model with guidance) BEFORE calling this. At most three takes per scene (the first and two redos).",
    promptSnippet: "redo_scenes — re-render named scenes of a project after changing their text or seed, and wait",
    promptGuidelines: ["Before redo_scenes, change the scene's text or add [seed=N] in the project file; the tool refuses an unchanged scene."],
    parameters: Type.Object({
      project: Type.String({ description: "Project file path, e.g. stories/projects/13-my-film.txt" }),
      scenes: Type.String({ description: "Space-separated scene numbers to re-render, e.g. \"5 7\"" }),
    }),
    executionMode: "sequential",
    async execute(_id, params, signal, onUpdate) {
      if (activeRender) await refuseIfRendering("redo_scenes");
      const proj = resolveProject(params.project);
      await checkSyntax(proj.abs);
      const scenes = parseScenes(params.scenes);
      await lintDialogue(proj.abs, scenes);
      if (!scenes.length) throw new Error("redo_scenes needs scene numbers");
      const refused: string[] = [];
      for (const n of scenes) {
        if (n > proj.scenes) { refused.push(`scene ${n}: the project has ${proj.scenes} scenes`); continue; }
        const takes = takesOf(proj.dir, n);
        if (takes >= MAX_TAKES) { refused.push(`scene ${n}: already ${takes} takes (the limit); keep the best take and say so in the report`); continue; }
        const same = await unchangedSinceLastTake(proj.abs, proj.dir, n);
        if (same) refused.push(`scene ${n}: its text and seed are unchanged since the last take (${same}), so it would render the same clip; edit its text or add [seed=N] first`);
      }
      if (refused.length) throw new Error(`redo_scenes refused:\n${refused.join("\n")}`);
      const say = (s: string) => onUpdate?.({ content: [{ type: "text", text: s }] });
      const hold = await takeGpuHold("render", `${proj.name} redo ${scenes.join(" ")}`, say, signal);
      if (!hold) await refuseIfRendering("redo_scenes");
      try {
        const pre = await preflight();
        const settle = await unloadAndSettle(say, signal);
        if (!settle.ok) throw new Error(`GPU not clear after ${settle.seconds} s: ${JSON.stringify(settle)}`);
        const stopFile = path.join(proj.dir, "stop-after");
        if (fs.existsSync(stopFile)) fs.unlinkSync(stopFile);
        const log = fs.openSync(path.join(REPO, `logs/story-${proj.name}.log`), "a");
        const queueOffset = fs.existsSync(QUEUE_LOG) ? fs.statSync(QUEUE_LOG).size : 0;
        const launchedAt = Date.now();
        const child = spawn("zsh", [path.join(REPO, "stories/redo.sh"), proj.abs, ...scenes.map(String)], { cwd: REPO, detached: true, stdio: ["ignore", log, log], env: hold ? { ...process.env, HOLD_ID: hold.id } : process.env });
        child.unref();
        fs.closeSync(log);
        await attachGpuHold(hold, child.pid);
        activeRender = { name: proj.name, kind: "redo", started: launchedAt };
        // redo.sh does not write queue.log; completion comes from the child's exit and the stitched film's mtime
        return await waitAndReport({ name: proj.name, dir: proj.dir, portrait: proj.portrait, kind: "redo", launchedAt, queueOffset, doneRegex: /^\d\d:\d\d (NEVER-MATCHES) x$/m, child, sheetScenes: scenes, totalScenes: proj.scenes, onUpdate, signal, pre, settle });
      } finally {
        await releaseGpuHold(hold, `redo_scenes ${proj.name} returned`);
      }
    },
  });
  pi.registerTool({
    name: "keep_take",
    label: "Keep previous take",
    description: "Put the PREVIOUS take of a redone scene back into the film when it is better than the new one (2026-09-27: on 2026-09-26 a redo made the film's best close-up worse and the director could not go back). The current take is moved into a new redo-N/ folder (nothing is deleted) and the film is re-stitched. CPU only, no render. Use it after review_scenes shows a clip's previous take (top row) better than the new one (bottom row).",
    promptSnippet: "keep_take — put a scene's previous take back in the film (after a redo made it worse)",
    parameters: Type.Object({
      project: Type.String({ description: "Project file path, e.g. stories/projects/19-my-film.txt" }),
      scene: Type.Number({ description: "Scene number whose previous take to keep" }),
      accept_sync_fail: Type.Optional(Type.String({ description: "Only for a dialogue shot the sync gate refused: keep its CURRENT take anyway and record why (it goes into the film's sync report). No take is swapped when this is given." })),
    }),
    executionMode: "sequential",
    async execute(_id, params, signal) {
      await refuseIfRendering("keep_take");
      const proj = resolveProject(params.project);
      const n = params.scene;
      if (params.accept_sync_fail) {
        const a = await run("python3", [path.join(REPO, "rig/sync/gate.py"), "accept", proj.name, String(n), params.accept_sync_fail], { timeoutMs: 300_000, signal });
        if (a.code !== 0) throw new Error(`accept_sync_fail failed: ${(a.stdout + a.stderr).trim().slice(-600)}`);
        const st = await run("zsh", [path.join(REPO, "stories/story.sh"), proj.abs], { timeoutMs: 900_000, signal, env: { ...process.env, ONLY: String(n) } });
        return { content: [{ type: "text", text: `${a.stdout.trim()}\n${st.stdout.trim().split("\n").slice(-8).join("\n")}` }], details: {} };
      }
      const r = await run("zsh", [path.join(REPO, "stories/keep-take.sh"), proj.abs, String(n)], { timeoutMs: 600_000, signal });
      if (r.code !== 0) throw new Error(`keep_take failed: ${(r.stdout + r.stderr).trim().slice(-600)}`);
      return { content: [{ type: "text", text: r.stdout.trim().split("\n").slice(-6).join("\n") }], details: {} };
    },
  });
}
