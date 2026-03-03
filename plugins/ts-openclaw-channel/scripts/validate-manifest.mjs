import fs from "node:fs";
import path from "node:path";

function fail(message) {
  console.error(`[manifest-check] ${message}`);
  process.exit(1);
}

const root = process.cwd();
const pkgPath = path.join(root, "package.json");
const manifestPath = path.join(root, "openclaw.plugin.json");

if (!fs.existsSync(pkgPath)) fail("package.json not found");
if (!fs.existsSync(manifestPath)) fail("openclaw.plugin.json not found");

const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf-8"));
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));

if (!manifest.id || typeof manifest.id !== "string") fail("manifest.id must be a non-empty string");
if (!manifest.name || typeof manifest.name !== "string") fail("manifest.name must be a non-empty string");

const pkgExtensions = pkg?.openclaw?.extensions;
const manifestExtensions = manifest?.extensions;

if (!Array.isArray(pkgExtensions) || pkgExtensions.length === 0) {
  fail("package.json openclaw.extensions must be a non-empty array");
}
if (!Array.isArray(manifestExtensions) || manifestExtensions.length === 0) {
  fail("openclaw.plugin.json extensions must be a non-empty array");
}

const a = JSON.stringify(pkgExtensions);
const b = JSON.stringify(manifestExtensions);
if (a !== b) {
  fail(`extensions mismatch: package=${a}, manifest=${b}`);
}

console.log("[manifest-check] ok");
