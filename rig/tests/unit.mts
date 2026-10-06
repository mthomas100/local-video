import filmRig, { bashBlocked, bashBlockedEverywhere, isDirector, shapeContext, isFilmSkillPrompt, staleScenes, unchangedSinceLastTake, describeClips, stripSwapBanner, imagesThatFit, sceneLines, latestSyncLines } from "../film-rig.ts";
const handlers: Record<string, Function> = {}; const cmds: Record<string, any> = {}; const tools: Record<string, any> = {};
const entries: any[] = []; const sent: any[] = []; const notes: string[] = [];
const api: any = {
  on: (ev: string, h: Function) => { handlers[ev] = h; },
  registerCommand: (n: string, o: any) => { cmds[n] = o; },
  registerTool: (t: any) => { tools[t.name] = t; },
  appendEntry: (ct: string, d: any) => entries.push({ type: "custom", customType: ct, data: d }),
  sendUserMessage: (m: any) => sent.push(m),
};
filmRig(api);
const must = (c: boolean, what: string) => { if (!c) { console.error("FAIL:", what); process.exit(1); } console.log("ok:", what); };
must(!!cmds.film && !!cmds.rig, "commands rig and film registered");
must(["render_and_wait", "review_scenes", "redo_scenes"].every((n) => tools[n]), "three tools registered");
const ctx: any = { model: { provider: "local", id: "vision", input: ["text", "image"] }, hasUI: true, ui: { notify: (m: string) => notes.push(m) }, sessionManager: { getEntries: () => entries } };
await handlers.session_start({}, ctx);
must(notes.at(-1)!.includes("director=off"), "session_start reports director off: " + notes.at(-1));
let r = await handlers.before_agent_start({ systemPrompt: "BASE", prompt: "x" }, ctx);
must(r === undefined, "no system prompt change while director is off");
await cmds.film.handler("make a film about a fox who runs a bakery", ctx);
must(entries.some((e) => e.customType === "film-rig" && e.data.director === true), "director=true persisted as a session entry");
must(sent[0] === "make a film about a fox who runs a bakery", "brief sent as the first user message");
must(notes.at(-1)!.includes("director mode ON") && notes.at(-1)!.includes("llama-swap"), "notify says ON with swap lifecycle: " + notes.at(-1));
r = await handlers.before_agent_start({ systemPrompt: "BASE", prompt: "x" }, ctx);
must(typeof r?.systemPrompt === "string" && r.systemPrompt.startsWith("BASE") && r.systemPrompt.includes("You are the film director on this Mac"), "director prompt appended to the system prompt (" + r.systemPrompt.length + " chars)");
r = await handlers.before_agent_start({ systemPrompt: "BASE\nYou are the film director on this Mac already", prompt: "x" }, ctx);
must(r === undefined, "not appended twice when the launcher already added it");
// resume: a fresh session_start restores director from entries
notes.length = 0; await handlers.session_start({}, ctx);
must(notes.at(-1)!.includes("director=on"), "resume restores director=on from entries");
// a model without image input warns
ctx.model = { provider: "local", id: "flash", input: ["text"] }; await handlers.model_select({ model: ctx.model }, ctx);
notes.length = 0; await cmds.film.handler("", ctx);
must(notes.some((n) => n.includes("cannot see images")), "warns when the model cannot see images");
// ds4-serve lifecycle for a `model`-started engine
ctx.model = { provider: "ds4", id: "deepseek-v4-flash", input: ["text", "image"] }; await handlers.model_select({ model: ctx.model }, ctx);
notes.length = 0; await cmds.film.handler("status", ctx);
must(notes.at(-1)!.includes('"lifecycle": "ds4-serve"') && notes.at(-1)!.includes('"director": true'), "status shows ds4-serve lifecycle + director on");
notes.length = 0; await cmds.film.handler("", ctx);
must(notes.at(-1)!.includes("model stop"), "notify explains the ds4-serve stop/restart path: " + notes.at(-1)!.slice(0, 120));
await cmds.film.handler("off", ctx);
must(entries.at(-1).data.director === false, "director=false persisted");
r = await handlers.before_agent_start({ systemPrompt: "BASE", prompt: "x" }, ctx);
must(r === undefined, "no system prompt change after /film off");
// --- 2026-09-24: the bash guard blanks film-folder paths; commands that start renders stay blocked
for (const ok of ["ls ~/Videos/vidgen/nyc-2000-slavic-neon/", "open ~/Videos/vidgen/look-test/sheet-1-2-3.png",
  "cd ~/Videos/vidgen/nyc; ls; ffprobe -v error scene-1.mp4; afplay /System/Library/Sounds/Glass.aiff",
  "ffprobe \"$HOME/Videos/vidgen/x/x.mp4\"", "ls -la /home/me/Videos/vidgen", "zsh -n stories/projects/16-x.txt",
  "grep -n still stories/projects/18-x.txt", "open ~/Videos/vidgen/x/still-3.png"])
  must(!bashBlocked(ok), "guard allows: " + ok);
for (const bad of ["vidgen --no-open 'a cat'", "~/repos/local-video/bin/vidgen -o ~/Videos/vidgen/x.mp4 'p'",
  "zsh stories/story.sh p.txt", "zsh stories/redo.sh p.txt 3", "curl 127.0.0.1:8090/unload", "pkill -f ltx",
  "kill 123", "nohup zsh stories/run-queue.sh p &", "cd ~/Videos/vidgen/x && vidgen 'y'",
  "bin/still -o x.png 'Coit Tower'", "~/repos/imagegen/.venv/bin/mflux-generate-qwen-2.1 --prompt x",
  "grep -n clamp stories/[s]tory.sh", "zsh stories/[s]tory.sh p.txt", "\"vid\"gen 'a cat'", "zsh stories/re\\do.sh p 3"])
  must(bashBlocked(bad), "guard blocks: " + bad);
// --- context shaping: images shown once; thinking dropped only before the latest compaction
const img = { type: "image", data: "xx", mimeType: "image/png" };
const think = (t: string) => ({ type: "thinking", thinking: t });
let msgs: any[] = [
  { role: "user", content: [{ type: "text", text: "brief" }], timestamp: 1 },
  { role: "assistant", content: [think("old plan"), { type: "text", text: "a" }], timestamp: 2 },
  { role: "toolResult", toolName: "review_scenes", content: [{ type: "text", text: "sheet" }, img], timestamp: 3 },
];
let out = shapeContext(structuredClone(msgs));
must(out.images === 0 && out.messages[2].content[1].type === "image", "a sheet the model has not answered yet keeps its image");
msgs.push({ role: "assistant", content: [think("verdicts"), { type: "text", text: "scene 1 ok" }], timestamp: 4 },
          { role: "toolResult", toolName: "edit", content: [{ type: "text", text: "edited" }], timestamp: 5 });
out = shapeContext(structuredClone(msgs));
must(out.images === 1 && out.messages[2].content[1].type === "text" && out.messages[2].content[1].text.includes("shown to you once"), "an answered sheet becomes a one-line note");
must(out.thinking === 0 && out.messages[1].content[0].type === "thinking", "no compaction yet: every thinking block stays");
msgs = [{ role: "compactionSummary", summary: "s", tokensBefore: 70000, timestamp: 10 },
        { role: "assistant", content: [think("kept but stale")], timestamp: 8 },
        { role: "assistant", content: [think("stale"), { type: "toolCall", id: "t", name: "edit", arguments: {} }], timestamp: 9 },
        { role: "assistant", content: [think("fresh"), { type: "text", text: "next" }], timestamp: 11 }];
out = shapeContext(structuredClone(msgs));
must(out.thinking === 2 && out.messages[2].content.length === 1 && out.messages[2].content[0].type === "toolCall", "thinking before the compaction is dropped, tool calls kept");
must(out.messages[1].content[0].type === "text", "a thinking-only reply keeps a placeholder text");
must(out.messages[3].content[0].type === "thinking", "a reply after the compaction keeps its thinking");
// --- /skill:studio and /skill:film turn director mode on by themselves
must(isFilmSkillPrompt("/skill:studio a halloween film") && isFilmSkillPrompt('<skill name="studio" location="x">') && isFilmSkillPrompt("/skill:film x"), "film skills detected");
must(!isFilmSkillPrompt("/skill:vidgen a cat") && !isFilmSkillPrompt("tell me about the studio"), "other prompts are not");
entries.length = 0; director_reset: {
  ctx.model = { provider: "local", id: "vision-q4", input: ["text", "image"] }; await handlers.model_select({ model: ctx.model }, ctx);
  r = await handlers.before_agent_start({ systemPrompt: "BASE", prompt: "/skill:studio a halloween film" }, ctx);
  must(typeof r?.systemPrompt === "string" && r.systemPrompt.includes("You are the film director on this Mac"), "studio turns director mode on and appends the prompt");
  must(entries.some((e) => e.customType === "film-rig" && e.data.director === true && e.data.via === "skill"), "the switch is persisted in the session");
}
// --- the context handler returns shaped messages (no render running in the test)
const ctxc: any = { ...ctx, signal: undefined };
const res = await handlers.context({ messages: structuredClone(msgs.concat([])) }, ctxc);
must(res?.messages?.[2]?.content?.[0]?.type === "toolCall", "the context hook returns the shaped messages");
// --- 2026-09-26: a film folder holding another project's clips is refused, not silently reused by story.sh
{
  const os = await import("node:os"); const fsx = await import("node:fs"); const px = await import("node:path");
  const tmp = fsx.mkdtempSync(px.join(os.tmpdir(), "stale-"));
  const proj = px.join(tmp, "18-x.txt");
  fsx.writeFileSync(proj, `NAME=x; SECS=8; SEED=5; BIBLE='style.'\nSCENES=(\n"[noanchor] a new line one"\n"[noanchor] [quality] a new line two"\n"[noanchor] a new line three"\n)\n`);
  const dir = px.join(tmp, "film"); fsx.mkdirSync(dir);
  for (const n of [1, 2, 3]) fsx.writeFileSync(px.join(dir, `scene-${n}.mp4`), "");
  fsx.writeFileSync(px.join(dir, "scene-1.json"), JSON.stringify({ prompt: "an old line one style.", seed: 5, mode: "fast" }));
  fsx.writeFileSync(px.join(dir, "scene-2.json"), JSON.stringify({ prompt: "a new line two style.", seed: 5, mode: "quality" }));
  must(JSON.stringify(await staleScenes(proj, dir, 3)) === "[1]", "a clip from another line is stale; a matching one and one without a sidecar are not");
  must((await unchangedSinceLastTake(proj, dir, 2)) === "seed 5, quality mode", "the redo guard still sees an unchanged scene");
  must((await unchangedSinceLastTake(proj, dir, 1)) === "", "the redo guard lets a changed scene through");
  fsx.rmSync(tmp, { recursive: true, force: true });
}
// --- 2026-09-26 (rig/bench/review-bench.py, V1): one image per clip, the full asked line, at most 16 images
{
  const d = describeClips("no-such-film", [1, 2, 17], [1, 2]);
  must(d.includes("in this order: clip 1, clip 2.") && d.includes("then call review_scenes for 17"), "review text lists the clip images in order and asks for the clips left out next");
  must(d.includes('"clip N: asked ... / shows ... / keep or redo"') && !d.includes("row"), "review text asks for one line per clip, no sheet rows");
}
// --- 2026-10-04: a who-spoke image follows its clip and is explained (rig/sync/whospoke.py)
{
  const d = describeClips("no-such-film", [2, 3, 4], [2, 3], [], [{ scene: 3, speaker: "Aldemar" }]);
  must(d.includes("in this order: clip 2, clip 3, who-spoke 3.") && d.includes("framed in green") && d.includes('"who: <name> yes"'), "a who-spoke image is listed right after its clip and explained");
  must(d.includes("then call review_scenes for 4") && !d.includes("row"), "the clips left out are still asked for next, and no sheet rows");
}
// --- 2026-09-26: llama-swap's loading banner is not replayed as the model's reasoning
{
  const banner = "━━━━━\nllama-swap loading model: vision-q4\n\nSorry, the inference you have reached is not in service ..........\nTeaching the model manners ............\nDone! (23.36s)\n━━━━━\n \n";
  must(stripSwapBanner(banner + "The first three shots rendered.") === "The first three shots rendered.", "banner stripped, the model's own reasoning kept byte for byte");
  must(stripSwapBanner(banner) === "", "a banner-only thinking block becomes empty");
  must(stripSwapBanner("I think ━━━━━\nllama-swap loading model: x") === "I think ━━━━━\nllama-swap loading model: x", "only a leading banner is touched");
  const sm = shapeContext([{ role: "assistant", content: [{ type: "thinking", thinking: banner + "plan" }, { type: "toolCall", id: "t", name: "review_scenes", arguments: {} }], timestamp: 5 }]);
  must(sm.banners === 1 && sm.messages[0].content[0].thinking === "plan" && sm.messages[0].content[1].type === "toolCall", "shapeContext strips the banner and keeps the tool call");
}
// --- 2026-09-27: review batches fit pi's output budget; redone clips come as previous-vs-new
{
  // the 2026-09-26 case: about 60K estimated context in pi's 83,616 window; 13 images left 1,673 output tokens
  const n = imagesThatFit(59_786, 83_616, 3_000);
  must(n >= 1 && n <= 7 && 83_616 - 59_786 - 3_000 - 4_096 - n * 1_200 >= 8_000, `at 60K context the batch (${n}) leaves at least 8,000 output tokens`);
  must(imagesThatFit(12_000, 83_616, 3_000) === 8, "early in a film a batch is capped at 8");
  must(imagesThatFit(80_000, 83_616, 3_000) === 1, "a nearly full context still shows one clip");
  must(imagesThatFit(null, undefined, 2_000) >= 1, "unknown usage (right after compaction) falls back to a safe estimate");
  const d = describeClips("no-such-film", [2, 3, 4], [2, 3, 4], [3]);
  must(d.includes("Clips 3 were redone") && d.includes("keep_take"), "a redone clip is described as previous vs new, with keep_take");
  must(bashBlocked("zsh stories/redo.sh p 3") && !bashBlocked("ls ~/Videos/vidgen/x/redo-1"), "guard unchanged for redo.sh and film paths");
}
// --- 2026-09-27: CAST=( "..." ) lines are not scenes
{
  const txt = 'NAME=x\nCAST=(\n"pip|a man"\n  "moth|a woman"\n)\nSCENES=(\n"[noanchor] one"\n"[noanchor] two"\n)\n';
  must(sceneLines(txt).length === 2 && sceneLines(txt)[0].includes("one"), "only SCENES=( ... ) lines count as scenes");
  must(sceneLines('SCENES=(\n"a"\n"b"\n"c"\n)\n').length === 3, "a project without CAST is unchanged");
}
// --- 2026-09-27: the sync block shows each shot's latest verdict (planted test run 1's story log, abridged)
{
  const log = ["sync 5: PASS, offset -55 ms (audio late), conf 6.01 [in sync] → keep",
    "sync 2: FAIL, offset -249 ms (audio late), conf 8.51 [offset -249 ms (audio late)] → retake",
    "sync 3: FAIL, offset -479 ms (audio late), conf 3.48, words 3/11 → retake",
    "sync 4: UNMEASURABLE [no face found] → retake with the speaker's face in view through the line (32 px or more: any framing from close-up to full length)",
    "NOT STITCHED planted-sync-r1: the sync gate refused the shots above",
    "sync 2: PASS, offset -44 ms (audio late), conf 7.38 [in sync] → keep", "sync 2: PASS, offset -44 ms (audio late), conf 7.38 [in sync] → keep",
    "sync 3: PASS, offset -73 ms (audio late), conf 9.05 [in sync] → keep", "sync 3: PASS, offset -73 ms (audio late), conf 9.05 [in sync] → keep",
    "sync 4: FAIL, offset +300 ms (audio early), conf 5.0 → retake", "scene 4: no take passed; kept take 1 (FAIL, conf 5.0): sync 4: FAIL ...",
    "scene 4: no take passed; kept take 1 (FAIL, conf 5.0): sync 4: FAIL ..."].join("\n");
  const s = latestSyncLines(log);
  must(s.length === 5, `one line per shot plus the kept-take line (${s.length})`);
  must(s.filter((l) => l.startsWith("sync 2:")).length === 1 && s.some((l) => l.startsWith("sync 2: PASS")), "a redone shot shows only its new verdict");
  must(!s.some((l) => l.includes("-249 ms") || l.includes("-479 ms")), "no stale FAIL line from before the redo");
  must(s[s.length - 1].startsWith("scene 4: no take passed") && s.some((l) => l.startsWith("sync 5: PASS")), "the kept-take line comes last; untouched shots keep their line");
}
// --- 2026-10-04: the GPU hold. Film-only rules apply in director mode only; every session keeps a narrow guard
{
  for (const bad of ["~/repos/ds4/ds4-server --chdir ~/repos/ds4 -m x.gguf", "cd ~/repos/ds4 && ./ds4-serve qwen38",
    "nohup llama-server -m x.gguf &", "pkill -f ds4-server", "killall llama-swap", "time ds4-server -m x",
    "launchctl kickstart -k gui/501/com.example.llama-swap", "launchctl bootout gui/501/com.example.hold-gate",
    "hold off", "hold on \"benchmark\"", "~/.local/bin/hold release h1a2b3c", "ls; \"hold\" off"])
    must(bashBlockedEverywhere(bad), "every session blocks: " + bad);
  for (const ok of ["tail -f ~/.ds4/llama-swap.log", "grep ds4-server notes.md", "ps aux | grep llama-server", "kill 123",
    "nohup python3 server.py &", "launchctl list", "vidgen --no-open 'a cat'", "hold", "hold status", "hold run -- vidgen x",
    "cat ~/repos/local-rig/launchd/com.example.llama-swap.plist", "ls ~/repos/ds4/ds4-server"])
    must(!bashBlockedEverywhere(ok), "every session allows: " + ok);
  const img = { type: "image", data: "xx", mimeType: "image/png" };
  const two = () => [{ role: "toolResult", content: [img], timestamp: 1 }, { role: "assistant", content: [{ type: "text", text: "seen" }], timestamp: 2 }];
  must(shapeContext(two(), { imagesOnce: false }).images === 0, "outside director mode a session keeps its images");
  must(shapeContext(two()).images === 1, "the director's images are still shown once");
  await cmds.film.handler("off", ctx);
  await handlers.before_agent_start({ systemPrompt: "BASE", prompt: "x" }, ctx);
  must(!isDirector(), "not the director after /film off with a plain system prompt");
  const call = (command: string) => handlers.tool_call({ toolName: "bash", input: { command } }, ctx);
  must((await call("kill 123")) === undefined && (await call("nohup python3 x.py &")) === undefined, "a general session may kill its own processes and use nohup");
  must((await call("pkill -f ds4-server"))?.block === true, "a general session may not kill a model server");
  process.env.FILM_RIG_DIRECTOR = "1";
  must(isDirector() && (await call("kill 123"))?.block === true, "rig/film-pi.sh's FILM_RIG_DIRECTOR=1 brings back the director's full list");
  delete process.env.FILM_RIG_DIRECTOR;
  await handlers.before_agent_start({ systemPrompt: "BASE\n\nYou are the film director on this Mac", prompt: "x" }, ctx);
  must(isDirector(), "the director prompt in the system prompt means director mode");
  await handlers.before_agent_start({ systemPrompt: "BASE", prompt: "x" }, ctx);
}
console.log("ALL OK");
