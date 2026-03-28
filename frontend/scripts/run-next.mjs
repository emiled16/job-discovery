import { spawn } from "node:child_process";

import { loadConfig } from "./validate-config.mjs";

const command = process.argv[2];
const config = loadConfig();

const argsByCommand = {
  build: ["next", "build"],
  dev: ["next", "dev", "--hostname", "0.0.0.0", "--port", String(config.port)],
  start: ["next", "start", "--hostname", "0.0.0.0", "--port", String(config.port)],
};

const args = argsByCommand[command];

if (!args) {
  throw new Error(`Unsupported Next.js command: ${command}`);
}

const child = spawn("npx", args, {
  stdio: "inherit",
  env: {
    ...process.env,
    PORT: String(config.port),
  },
});

child.on("exit", (code) => {
  process.exit(code ?? 1);
});
