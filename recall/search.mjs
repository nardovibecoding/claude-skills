#!/usr/bin/env node
/**
 * Hybrid memory search — Vector + BM25 + Recency + Graph + Cross-encoder reranker.
 * Section-level chunking for long docs.
 *
 * Usage: node search.mjs "how did we fix the matcher?"
 *        node search.mjs "gbrain" --json    (for hook auto-inject)
 *        node search.mjs "x" --no-rerank    (skip reranker)
 *
 * Pipeline:
 *   1. Split each file body by `##` headings → chunks (max 8/file, 500 chars each)
 *   2. Vector: per-chunk embeddings via all-MiniLM-L6-v2 (file score = max chunk)
 *   3. BM25: TF-IDF with field weighting (name 3x, desc 2x, body 1x) — file-level
 *   4. Recency: mtime-based boost
 *   5. Graph: traverse graph.json for related nodes
 *   6. Fuse: Reciprocal Rank Fusion (k=60) → top 20
 *   7. Rerank: cross-encoder ms-marco-MiniLM-L-6-v2 scores (query, doc) pairs → top 5
 *
 * Cache: ~/.claude/.memory_embeddings_cache.v2.json (chunk-aware schema)
 */

import { readFileSync, writeFileSync, existsSync, readdirSync, statSync } from "fs";
import { join } from "path";
import { homedir } from "os";

const CLAUDE_DIR = join(homedir(), ".claude");
const PROJECTS_DIR = join(CLAUDE_DIR, "projects");
const NARDOWORLD_DIR = join(homedir(), "NardoWorld");
const CACHE_FILE = join(CLAUDE_DIR, ".memory_embeddings_cache.v2.json");
const GRAPH_FILE = join(homedir(), "telegram-claude-bot", "graphify-out", "graph.json");

const args = process.argv.slice(2);
const jsonMode = args.includes("--json");
const noRerank = args.includes("--no-rerank");
const query = args.filter(a => !a.startsWith("--"))[0];
if (!query) {
  console.error("Usage: node search.mjs \"<query>\" [--json] [--no-rerank]");
  process.exit(1);
}

const MAX_CHUNKS_PER_FILE = 8;
const CHUNK_MAX_CHARS = 500;
const RERANK_CANDIDATES = 20;
const TOP_K = 5;

// ---------------------------------------------------------------------------
// File discovery
// ---------------------------------------------------------------------------

function findFilesRecursive(dir, source) {
  const results = [];
  if (!existsSync(dir)) return results;
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory() && !entry.name.startsWith('.') && entry.name !== '__pycache__' && entry.name !== 'node_modules') {
      results.push(...findFilesRecursive(fullPath, source));
    } else if (entry.isFile() && entry.name.endsWith('.md') && entry.name !== 'MEMORY.md' && entry.name !== '_index.md') {
      const stat = statSync(fullPath);
      results.push({ path: fullPath, project: source, name: entry.name, mtime: stat.mtimeMs });
    }
  }
  return results;
}

function findMemoryFiles() {
  const files = [];
  if (existsSync(PROJECTS_DIR)) {
    for (const project of readdirSync(PROJECTS_DIR)) {
      const memDir = join(PROJECTS_DIR, project, "memory");
      files.push(...findFilesRecursive(memDir, project));
    }
  }
  files.push(...findFilesRecursive(NARDOWORLD_DIR, "NardoWorld"));
  return files;
}

// ---------------------------------------------------------------------------
// Frontmatter + chunking
// ---------------------------------------------------------------------------

function parseFrontmatter(text) {
  const m = text.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)/);
  if (!m) return { fm: {}, body: text.trim() };
  const fm = {};
  for (const line of m[1].split("\n")) {
    const idx = line.indexOf(":");
    if (idx > 0) fm[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
  }
  return { fm, body: m[2].trim() };
}

/**
 * Split body by `##`/`###` headings into chunks. First chunk = preamble.
 * Each chunk: {heading, text (≤CHUNK_MAX_CHARS)}. Capped at MAX_CHUNKS_PER_FILE.
 * Short files (<CHUNK_MAX_CHARS total) return a single chunk.
 */
function chunkBody(body, name, desc) {
  if (body.length <= CHUNK_MAX_CHARS) {
    return [{ heading: "", text: body }];
  }
  const lines = body.split("\n");
  const chunks = [];
  let curHead = "";
  let curBuf = [];

  const flush = () => {
    if (!curBuf.length) return;
    const text = curBuf.join("\n").slice(0, CHUNK_MAX_CHARS).trim();
    if (text) chunks.push({ heading: curHead, text });
  };

  for (const line of lines) {
    const h = line.match(/^(#{2,3})\s+(.+)/);
    if (h) {
      flush();
      curHead = h[2].trim();
      curBuf = [];
    } else {
      curBuf.push(line);
    }
  }
  flush();

  if (chunks.length === 0) return [{ heading: "", text: body.slice(0, CHUNK_MAX_CHARS) }];
  return chunks.slice(0, MAX_CHUNKS_PER_FILE);
}

// ---------------------------------------------------------------------------
// BM25 (file-level)
// ---------------------------------------------------------------------------

function tokenize(text) {
  return text.toLowerCase().replace(/[^a-z0-9_\-]/g, " ").split(/\s+/).filter(t => t.length > 1);
}

function bm25Search(docs, queryText, k1 = 1.5, b = 0.75) {
  const qTokens = tokenize(queryText);
  if (qTokens.length === 0) return docs.map(() => 0);
  const N = docs.length;
  const tdocs = docs.map(tokenize);
  const avgDl = tdocs.reduce((s, d) => s + d.length, 0) / N || 1;
  const df = {};
  for (const qt of qTokens) {
    df[qt] = 0;
    for (const doc of tdocs) if (doc.includes(qt)) df[qt]++;
  }
  return tdocs.map(docTokens => {
    const dl = docTokens.length;
    const tf = {};
    for (const t of docTokens) tf[t] = (tf[t] || 0) + 1;
    let score = 0;
    for (const qt of qTokens) {
      const termFreq = tf[qt] || 0;
      if (termFreq === 0) continue;
      const idf = Math.log((N - df[qt] + 0.5) / (df[qt] + 0.5) + 1);
      const tfNorm = (termFreq * (k1 + 1)) / (termFreq + k1 * (1 - b + b * (dl / avgDl)));
      score += idf * tfNorm;
    }
    return score;
  });
}

// ---------------------------------------------------------------------------
// Embedding + reranker
// ---------------------------------------------------------------------------

let embedder = null;
let reranker = null;

async function getEmbedder() {
  if (embedder) return embedder;
  const { pipeline } = await import("@huggingface/transformers");
  embedder = await pipeline("feature-extraction", "Xenova/all-MiniLM-L6-v2", { dtype: "fp32" });
  return embedder;
}

async function getReranker() {
  if (reranker) return reranker;
  const mod = await import("@huggingface/transformers");
  // Call model + tokenizer directly — text-classification pipeline applies softmax
  // over the single-label head, which clamps every ms-marco cross-encoder score to 1.0.
  // We want the raw logit (regression-style relevance).
  const tokenizer = await mod.AutoTokenizer.from_pretrained("Xenova/ms-marco-MiniLM-L-6-v2");
  const model = await mod.AutoModelForSequenceClassification.from_pretrained(
    "Xenova/ms-marco-MiniLM-L-6-v2",
    { dtype: "fp32" },
  );
  reranker = { tokenizer, model };
  return reranker;
}

async function embed(texts) {
  const model = await getEmbedder();
  const output = await model(texts, { pooling: "mean", normalize: true });
  const data = output.data;
  const dim = output.dims[output.dims.length - 1];
  const vectors = [];
  for (let i = 0; i < texts.length; i++) {
    const vec = new Float32Array(dim);
    for (let k = 0; k < dim; k++) vec[k] = data[i * dim + k];
    vectors.push(Array.from(vec));
  }
  return vectors;
}

function cosineSim(a, b) {
  let dot = 0;
  for (let i = 0; i < a.length; i++) dot += a[i] * b[i];
  return dot;
}

/**
 * Rerank candidates with cross-encoder. Returns array of {index, score} sorted desc.
 * Passages use name + heading + text (section-aware).
 */
async function rerank(query, candidates) {
  if (candidates.length <= 1) return candidates.map(c => ({ index: c.index, score: 1 }));
  const { tokenizer, model } = await getReranker();
  // Tokenize (query, passage) pairs. Pad/truncate to 512 tokens (cross-encoder default).
  const texts = candidates.map(() => query);
  const pairs = candidates.map(c => c.passage);
  const inputs = await tokenizer(texts, {
    text_pair: pairs,
    padding: true,
    truncation: true,
    max_length: 512,
    return_tensors: "pt",
  });
  const output = await model(inputs);
  // ms-marco has 1 output logit per (query, passage). Raw logit = relevance.
  const logits = output.logits.data;
  const scored = candidates.map((c, i) => ({ index: c.index, score: logits[i], passage: c.passage }));
  return scored.sort((a, b) => b.score - a.score);
}

// ---------------------------------------------------------------------------
// Recency
// ---------------------------------------------------------------------------

function recencyRanked(files) {
  const now = Date.now();
  const SEVEN_DAYS = 7 * 24 * 60 * 60 * 1000;
  return files.map((f, index) => {
    const age = now - f.mtime;
    const score = age < SEVEN_DAYS ? 1.0 - (age / SEVEN_DAYS) * 0.5 : 0.5 * Math.exp(-(age - SEVEN_DAYS) / (30 * 24 * 60 * 60 * 1000));
    return { index, score };
  }).sort((a, b) => b.score - a.score);
}

// ---------------------------------------------------------------------------
// Graph expansion
// ---------------------------------------------------------------------------

let graphData = null;
function loadGraph() {
  if (graphData !== null) return graphData;
  if (!existsSync(GRAPH_FILE)) { graphData = false; return false; }
  try { graphData = JSON.parse(readFileSync(GRAPH_FILE, "utf-8")); return graphData; }
  catch { graphData = false; return false; }
}

function graphExpand(topFilePaths) {
  const graph = loadGraph();
  if (!graph || !graph.nodes) return new Set();
  const matchedNodeIds = new Set();
  for (const node of graph.nodes) {
    const sf = node.source_file || "";
    if (!sf) continue;
    for (const fp of topFilePaths) {
      const fpBase = fp.split("/").pop().replace(".md", "");
      const sfBase = sf.split("/").pop().replace(/\.\w+$/, "");
      if (fpBase === sfBase || sf.includes(fpBase) || fp.includes(sfBase)) {
        matchedNodeIds.add(node.id);
      }
    }
  }
  const neighborIds = new Set();
  if (graph.links) {
    for (const link of graph.links) {
      if (matchedNodeIds.has(link.source)) neighborIds.add(link.target);
      if (matchedNodeIds.has(link.target)) neighborIds.add(link.source);
    }
  }
  const expandedFiles = new Set();
  for (const node of graph.nodes) {
    if (neighborIds.has(node.id) && !matchedNodeIds.has(node.id)) {
      const sf = node.source_file || "";
      if (sf) expandedFiles.add(sf.split("/").pop().replace(/\.\w+$/, ""));
    }
  }
  return expandedFiles;
}

// ---------------------------------------------------------------------------
// RRF
// ---------------------------------------------------------------------------

function reciprocalRankFusion(rankedLists, k = 60) {
  const fused = {};
  for (const ranked of rankedLists) {
    for (let rank = 0; rank < ranked.length; rank++) {
      const idx = ranked[rank].index;
      if (!fused[idx]) fused[idx] = 0;
      fused[idx] += 1 / (k + rank + 1);
    }
  }
  return Object.entries(fused)
    .map(([index, score]) => ({ index: parseInt(index), score }))
    .sort((a, b) => b.score - a.score);
}

// ---------------------------------------------------------------------------
// Cache (chunk-aware)
// ---------------------------------------------------------------------------

function loadCache() {
  if (!existsSync(CACHE_FILE)) return {};
  try { return JSON.parse(readFileSync(CACHE_FILE, "utf-8")); }
  catch { return {}; }
}

function saveCache(cache) {
  writeFileSync(CACHE_FILE, JSON.stringify(cache));
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const files = findMemoryFiles();
  if (files.length === 0) { console.log("No memory files found."); process.exit(0); }

  // Parse each file once
  const fileParsed = files.map(f => parseFrontmatter(readFileSync(f.path, "utf-8")));

  // Build chunks per file
  const fileChunks = files.map((f, i) => {
    const name = f.name.replace(".md", "").replace(/_/g, " ");
    const desc = fileParsed[i].fm.description || "";
    return chunkBody(fileParsed[i].body, name, desc);
  });

  // BM25 per-file (uses repeated name/desc for field weighting)
  const bm25Docs = files.map((f, i) => {
    const name = f.name.replace(".md", "").replace(/_/g, " ");
    const desc = fileParsed[i].fm.description || "";
    const bodyTxt = fileChunks[i].map(c => c.text).join(" ").slice(0, 3000);
    return `${name} ${name} ${name} ${desc} ${desc} ${bodyTxt}`;
  });
  const bm25Scores = bm25Search(bm25Docs, query);
  const bm25Ranked = bm25Scores.map((score, index) => ({ index, score }))
    .filter(r => r.score > 0).sort((a, b) => b.score - a.score);

  // Chunked embeddings
  const cache = loadCache();
  const toEmbed = [];
  const toEmbedMeta = [];

  for (let i = 0; i < files.length; i++) {
    const f = files[i];
    const chunks = fileChunks[i];
    const name = f.name.replace(".md", "").replace(/_/g, " ");
    const desc = fileParsed[i].fm.description || "";
    const existing = cache[f.path];

    if (existing && existing.mtime >= f.mtime && existing.chunks?.length === chunks.length) continue;

    for (let ci = 0; ci < chunks.length; ci++) {
      const c = chunks[ci];
      const chunkText = `${name}${c.heading ? " — " + c.heading : ""}: ${desc} ${c.text}`.slice(0, 1000);
      toEmbed.push(chunkText);
      toEmbedMeta.push({ fileIdx: i, chunkIdx: ci, heading: c.heading });
    }
  }

  if (toEmbed.length > 0) {
    const BATCH_SIZE = 16;
    process.stderr.write(`Embedding ${toEmbed.length} chunks (batch=${BATCH_SIZE})...\n`);
    for (let b = 0; b < toEmbed.length; b += BATCH_SIZE) {
      const batchTexts = toEmbed.slice(b, b + BATCH_SIZE);
      const batchMeta = toEmbedMeta.slice(b, b + BATCH_SIZE);
      const vectors = await embed(batchTexts);
      for (let j = 0; j < batchMeta.length; j++) {
        const { fileIdx, chunkIdx, heading } = batchMeta[j];
        const f = files[fileIdx];
        if (!cache[f.path] || cache[f.path].mtime < f.mtime) {
          cache[f.path] = { mtime: f.mtime, name: f.name, project: f.project, chunks: [] };
        }
        cache[f.path].chunks[chunkIdx] = { heading, vector: vectors[j] };
      }
      if (b + BATCH_SIZE < toEmbed.length) {
        saveCache(cache);
        process.stderr.write(`  ${Math.min(b + BATCH_SIZE, toEmbed.length)}/${toEmbed.length}\n`);
      }
    }
    saveCache(cache);
  }

  // Query vector + per-file max chunk score
  const [queryVec] = await embed([query]);

  const vectorScores = files.map((f, i) => {
    const entry = cache[f.path];
    if (!entry?.chunks?.length) return { index: i, score: 0, bestChunk: 0 };
    let best = 0, bestIdx = 0;
    for (let ci = 0; ci < entry.chunks.length; ci++) {
      const v = entry.chunks[ci]?.vector;
      if (!v) continue;
      const s = cosineSim(queryVec, v);
      if (s > best) { best = s; bestIdx = ci; }
    }
    return { index: i, score: best, bestChunk: bestIdx };
  });
  const vectorRanked = [...vectorScores].sort((a, b) => b.score - a.score);

  // Recency
  const recencyRank = recencyRanked(files);

  // RRF
  const fused = reciprocalRankFusion([vectorRanked, bm25Ranked, recencyRank]);

  // Graph boost on top-5 neighbors
  const topFilePaths = fused.slice(0, 5).map(r => files[r.index].path);
  const graphNeighbors = graphExpand(topFilePaths);
  if (graphNeighbors.size > 0) {
    for (const r of fused.slice(5, 20)) {
      const fBase = files[r.index].name.replace(".md", "");
      for (const gf of graphNeighbors) {
        if (fBase === gf || fBase.includes(gf) || gf.includes(fBase)) {
          r.score += 0.005;
          r.graphBoosted = true;
          break;
        }
      }
    }
    fused.sort((a, b) => b.score - a.score);
  }

  // Cross-encoder rerank on top-N candidates
  let final = fused.slice(0, TOP_K);
  let rerankedLabels = null;
  if (!noRerank && fused.length > 1) {
    const candidates = fused.slice(0, RERANK_CANDIDATES).map(r => {
      const f = files[r.index];
      const bc = vectorScores[r.index].bestChunk ?? 0;
      const chunk = fileChunks[r.index][bc] || fileChunks[r.index][0];
      const name = f.name.replace(".md", "").replace(/_/g, " ");
      const desc = fileParsed[r.index].fm.description || "";
      const passage = `${name}: ${desc} ${chunk.text}`.slice(0, 512);
      return { index: r.index, rrfScore: r.score, passage, graphBoosted: r.graphBoosted };
    });
    try {
      const reranked = await rerank(query, candidates);
      rerankedLabels = new Map(reranked.map((r, i) => [r.index, i]));
      final = reranked.slice(0, TOP_K).map(r => {
        const cand = candidates.find(c => c.index === r.index);
        return { index: r.index, score: r.score, rrfScore: cand.rrfScore, graphBoosted: cand.graphBoosted };
      });
    } catch (err) {
      process.stderr.write(`[rerank failed: ${err.message}] — falling back to RRF order\n`);
    }
  }

  // Output
  if (jsonMode) {
    const results = final.map(r => {
      const f = files[r.index];
      const desc = fileParsed[r.index].fm.description || "";
      return {
        score: r.score.toFixed(4),
        rrfScore: (r.rrfScore ?? r.score).toFixed(4),
        source: f.project === "NardoWorld" ? "wiki" : "mem",
        file: f.name,
        path: f.path,
        description: desc.slice(0, 120),
        graphBoosted: !!r.graphBoosted,
      };
    });
    console.log(JSON.stringify(results));
  } else {
    console.log(`Query: "${query}"\n`);
    const totalChunks = Object.values(cache).reduce((s, e) => s + (e.chunks?.length || 0), 0);
    console.log(`  ${files.length} files, ${totalChunks} chunks | BM25 hits: ${bm25Ranked.length} | Graph: ${graphNeighbors.size} | Rerank: ${noRerank ? "skipped" : "on"}\n`);

    for (const r of final) {
      const f = files[r.index];
      const vecScore = vectorScores[r.index].score;
      const bm25Score = bm25Scores[r.index];
      const barLen = Math.max(0, Math.min(30, Math.round(r.score * (noRerank ? 600 : 3))));
      const bar = "█".repeat(barLen);
      const tag = r.graphBoosted ? " [G]" : "";
      const rrfTag = r.rrfScore != null ? ` rrf=${r.rrfScore.toFixed(3)}` : "";

      console.log(`  [${noRerank ? "RRF" : "RR"} ${r.score.toFixed(4)}]${rrfTag} ${bar}${tag}`);
      console.log(`  vec=${vecScore.toFixed(3)}  bm25=${bm25Score.toFixed(2)}`);
      const label = f.project === "NardoWorld" ? "wiki" : "mem";
      console.log(`  [${label}] ${f.name}`);
      console.log(`  ${f.path}\n`);
    }
  }
}

main().catch(err => { console.error("Error:", err.message); process.exit(1); });
