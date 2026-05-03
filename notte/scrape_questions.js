/**
 * Yojana Mitra — Bulk Question Scraper
 * =====================================
 * Calls your Notte function for every scheme in all_schemes_export.json,
 * fetches eligibility questions, and merges them back in.
 *
 * SETUP:
 *   1. Put this file in the same folder as all_schemes_export.json
 *   2. Set your NOTTE_API_KEY below (from https://console.notte.cc/api-keys)
 *   3. node scrape_questions.js
 *
 * OUTPUT:
 *   schemes_with_questions.json  — all 4226 schemes + eligibilityQuestions[]
 *   questions_only.json          — slim { id, name, slug, questions[] } list
 *   failed_slugs.json            — schemes that got 0 questions (wrong slug guess)
 *   scrape_progress.json         — checkpoint: auto-resumes if you stop and restart
 */

const fs = require("fs");

// ─── YOUR CONFIG HERE ─────────────────────────────────────────────────────────
const NOTTE_API_KEY = "sk-notte-b19dd8884731bbd2a80b24b4af25764c5def2d21ec1e30a4683711535fc701ce";           // ← paste your key
const NOTTE_FUNCTION_ID = "c0a56ecf-043d-47a5-a1f7-b791197a4334";
const SCHEMES_FILE      = "./all_schemes_export.json";
const OUTPUT_FULL       = "./schemes_with_questions.json";
const OUTPUT_SLIM       = "./questions_only.json";
const OUTPUT_FAILED     = "./failed_slugs.json";
const PROGRESS_FILE     = "./scrape_progress.json";
const CONCURRENCY       = 5;     // parallel Notte calls at a time
const DELAY_BETWEEN_BATCHES_MS = 500;  // ms between batches
const RETRY_LIMIT       = 2;     // retries on network error
// ─────────────────────────────────────────────────────────────────────────────

// ─── SLUG DERIVATION ─────────────────────────────────────────────────────────
// Your schemes have no slug field, so we guess it from the scheme name.
// Rule: prefer the ACRONYM in parentheses → "Pradhan Mantri Jan Dhan Yojana (PMJDY)" → "pmjdy"
// Fallback: slugify the full name → "Stand Up India Scheme" → "stand-up-india-scheme"
function deriveSlug(name) {
  const match = name.match(/\(([A-Z][A-Z0-9\-]{1,})\)/);
  if (match) return match[1].toLowerCase().replace(/-/g, "");
  return name
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 50);
}
// ─────────────────────────────────────────────────────────────────────────────

// ─── NOTTE API CALL ──────────────────────────────────────────────────────────
async function fetchQuestionsFromNotte(slug) {
  const url = `https://api.notte.cc/functions/${NOTTE_FUNCTION_ID}/runs/start`;

  for (let attempt = 1; attempt <= RETRY_LIMIT + 1; attempt++) {
    let res;
    try {
      res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type":  "application/json",
          "Authorization": `Bearer ${NOTTE_API_KEY}`,
        },
        body: JSON.stringify({ vars: { slug } }),
      });
    } catch (e) {
      if (attempt > RETRY_LIMIT) return { questions: [], error: `Network: ${e.message}` };
      await sleep(600 * attempt);
      continue;
    }

    if (!res.ok) {
      const body = await res.text().catch(() => "");
      if (attempt > RETRY_LIMIT) return { questions: [], error: `HTTP ${res.status}: ${body.slice(0, 100)}` };
      await sleep(600 * attempt);
      continue;
    }

    let data;
    try {
      data = await res.json();
    } catch (e) {
      return { questions: [], error: "JSON parse failed" };
    }

    // Notte returns the function output in data.result or data.output or at root
    const result    = data?.result ?? data?.output ?? data;
    const questions = result?.questions ?? [];
    return { questions };
  }

  return { questions: [], error: "Max retries exceeded" };
}
// ─────────────────────────────────────────────────────────────────────────────

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function loadProgress() {
  if (fs.existsSync(PROGRESS_FILE)) {
    return JSON.parse(fs.readFileSync(PROGRESS_FILE, "utf-8"));
  }
  return { done: {}, errors: {} };
}

function saveProgress(p) {
  fs.writeFileSync(PROGRESS_FILE, JSON.stringify(p, null, 2));
}

// ─── MAIN ────────────────────────────────────────────────────────────────────
async function main() {
  console.log("═══════════════════════════════════════════════════════");
  console.log("  Yojana Mitra — Question Scraper via Notte");
  console.log("═══════════════════════════════════════════════════════\n");

  if (NOTTE_API_KEY === "YOUR_NOTTE_API_KEY_HERE") {
    console.error("❌  Set your NOTTE_API_KEY at the top of this file first.");
    process.exit(1);
  }

  const schemes = JSON.parse(fs.readFileSync(SCHEMES_FILE, "utf-8"));
  console.log(`✓ Loaded ${schemes.length} schemes`);

  const progress = loadProgress();
  const cached = Object.keys(progress.done).length;
  if (cached > 0) console.log(`↩ Resuming — ${cached} slugs already done\n`);

  // Only process schemes not already done
  const todo = schemes.filter(s => !(deriveSlug(s.name) in progress.done));
  console.log(`→ ${todo.length} to scrape | Concurrency: ${CONCURRENCY}\n`);

  let done = 0;
  const total = todo.length;

  for (let i = 0; i < todo.length; i += CONCURRENCY) {
    const batch = todo.slice(i, i + CONCURRENCY);

    await Promise.all(batch.map(async (scheme) => {
      const slug = deriveSlug(scheme.name);
      const { questions, error } = await fetchQuestionsFromNotte(slug);

      progress.done[slug] = questions;
      if (error) progress.errors[slug] = error;
      done++;

      const icon = questions.length > 0 ? "✓" : "✗";
      console.log(`  [${done}/${total}] ${icon} ${slug.padEnd(38)} ${questions.length}q${error ? " — " + error : ""}`);
    }));

    saveProgress(progress);
    writeOutputs(schemes, progress);

    if (i + CONCURRENCY < todo.length) await sleep(DELAY_BETWEEN_BATCHES_MS);
  }

  writeOutputs(schemes, progress);
  printSummary(schemes, progress);
}

function writeOutputs(schemes, progress) {
  const full    = [];
  const slim    = [];
  const failed  = [];

  for (const scheme of schemes) {
    const slug      = deriveSlug(scheme.name);
    const questions = progress.done[slug] ?? [];
    const error     = progress.errors?.[slug];

    full.push({ ...scheme, slug, eligibilityQuestions: questions });
    slim.push({ id: scheme.id, name: scheme.name, slug, questions });

    if (questions.length === 0) {
      failed.push({ id: scheme.id, name: scheme.name, slug, error: error ?? "no questions" });
    }
  }

  fs.writeFileSync(OUTPUT_FULL,   JSON.stringify(full,   null, 2));
  fs.writeFileSync(OUTPUT_SLIM,   JSON.stringify(slim,   null, 2));
  fs.writeFileSync(OUTPUT_FAILED, JSON.stringify(failed, null, 2));
}

function printSummary(schemes, progress) {
  const withQ    = schemes.filter(s => (progress.done[deriveSlug(s.name)] ?? []).length > 0).length;
  const withoutQ = schemes.length - withQ;
  const totalQ   = Object.values(progress.done).reduce((acc, q) => acc + q.length, 0);

  console.log("\n═══════════════════════════════════════════════════════");
  console.log("  DONE!");
  console.log(`  ✓ Schemes with questions : ${withQ}`);
  console.log(`  ✗ No questions (bad slug) : ${withoutQ}`);
  console.log(`  ∑ Total questions scraped : ${totalQ}`);
  console.log(`\n  Files written:`);
  console.log(`    ${OUTPUT_FULL}   ← use this in Yojana Mitra`);
  console.log(`    ${OUTPUT_SLIM}        ← slim lookup table`);
  console.log(`    ${OUTPUT_FAILED}      ← fix slugs for these`);
  console.log("═══════════════════════════════════════════════════════");
  console.log(`\n  ℹ Open failed_slugs.json, find the correct slug from`);
  console.log(`    myscheme.gov.in/schemes/<slug>, add it to a manual`);
  console.log(`    overrides map in deriveSlug(), and re-run.\n`);
}

main().catch(e => { console.error("Fatal:", e); process.exit(1); });
