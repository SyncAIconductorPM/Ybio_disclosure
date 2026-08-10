#!/usr/bin/env node
import { mkdirSync, copyFileSync, cpSync, existsSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const out = join(root, "public");
mkdirSync(out, { recursive: true });

for (const name of readdirSync(root)) {
  if (name.endsWith(".html")) {
    copyFileSync(join(root, name), join(out, name));
  }
}
for (const dir of ["css", "js", "design", "samples", "templates"]) {
  const src = join(root, dir);
  if (existsSync(src)) cpSync(src, join(out, dir), { recursive: true });
}
writeFileSync(join(out, ".vercel-static-ok"), new Date().toISOString());
console.log("[build] public/ ready");
process.exit(0);
