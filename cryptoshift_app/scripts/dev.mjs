// Starts the API (port 8787) and the Vite dev server (port 5173) together.
import { spawn } from "node:child_process";
const isWin = process.platform === "win32";
const run = (name, cmd, args, opts = {}) => {
  const child = spawn(cmd, args, { stdio: "inherit", shell: isWin, ...opts });
  child.on("exit", (code) => {
    console.log(`[${name}] exited with ${code}`);
    process.exit(code ?? 0);
  });
  return child;
};
const api = run("api", process.execPath, ["backend/src/server.js"]);
const web = run("web", isWin ? "npm.cmd" : "npm", ["--prefix", "frontend", "run", "dev"]);
const stop = () => { api.kill(); web.kill(); };
process.on("SIGINT", stop);
process.on("SIGTERM", stop);
