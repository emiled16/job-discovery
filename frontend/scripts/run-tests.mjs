import { spawn } from "node:child_process";

const rawArgs = process.argv.slice(2);
const watchMode = rawArgs.includes("--watch");
const passthroughArgs = rawArgs.filter((arg) => arg !== "--watch" && arg !== "--runInBand");

const child = spawn(
  "npx",
  ["vitest", watchMode ? undefined : "run", ...passthroughArgs].filter(Boolean),
  {
    stdio: "inherit",
    env: process.env,
  },
);

child.on("exit", (code) => {
  process.exit(code ?? 1);
});
