// Real integration run of render_and_wait on the two-scene smoke project, no pi UI.
// LIFECYCLE=swap  -> the model is expected loaded in llama-swap; the tool must unload it, render, report.
// LIFECYCLE=ds4   -> an engine started with `model <target>` is up; the tool must `model stop`, render, `model <target>`.
import filmRig from "../film-rig.ts";
const handlers: Record<string, Function> = {}; const tools: Record<string, any> = {};
const api: any = { on: (ev: string, h: Function) => { handlers[ev] = h; }, registerCommand: () => {}, registerTool: (t: any) => { tools[t.name] = t; }, appendEntry: () => {}, sendUserMessage: () => {} };
filmRig(api);
const ds4 = process.env.LIFECYCLE === "ds4";
const model = ds4 ? { provider: "ds4", id: "deepseek-v4-flash", input: ["text", "image"] } : { provider: "local", id: "vision", input: ["text", "image"] };
const ctx: any = { model, hasUI: false, sessionManager: { getEntries: () => [] } };
await handlers.session_start({}, ctx);
const ts = () => new Date().toISOString().slice(11, 19);
const t0 = Date.now();
const res = await tools.render_and_wait.execute("t1", { project: "stories/projects/00-rig-smoke.txt", sheet: "1 2" }, undefined,
  (u: any) => console.log(ts(), "update:", String(u.content?.[0]?.text ?? "").replace(/\n/g, " ").slice(0, 220)));
const text = res.content.filter((c: any) => c.type === "text").map((c: any) => c.text).join("\n");
console.log("----- report -----\n" + text.slice(0, 3000));
console.log("----- images:", res.content.filter((c: any) => c.type === "image").length, "status:", res.details?.status, "elapsed s:", Math.round((Date.now() - t0) / 1000));
