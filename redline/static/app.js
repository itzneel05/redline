"use strict";

/*
 * Redline's interface.
 *
 * The report is a document, not a list of cards: each finding is placed in the
 * margin beside the clause whose words triggered it, and those words are
 * underlined inside the clause. Placing a finding means finding its quote in
 * the pasted text, which is done by matching the longest run of words that
 * appears verbatim — the built-in checks quote a padded snippet, so the ends of
 * a quote are often cut mid-word.
 */

const $ = (id) => document.getElementById(id);

const RISK_LABEL = { high: "High risk", medium: "Medium risk", low: "Low risk" };
const RISK_ORDER = { high: 0, medium: 1, low: 2 };

const SAMPLE = [
  "DESIGN SERVICES AGREEMENT",
  "",
  "1. Scope. Designer will provide design services as requested by Client from time to time.",
  "Client may request unlimited revisions until Client is satisfied.",
  "",
  "2. Fees. Client shall pay the fee of $2,000 net 90 days from invoice.",
  "",
  "3. Payment. Payment is contingent upon Client's receipt of payment from its own customers.",
  "Client may withhold payment at its sole discretion if the deliverables are not to Client's satisfaction.",
  "",
  "4. Intellectual Property. All work shall be considered work for hire and Designer assigns all right, title,",
  "and interest in all intellectual property to Client, including any pre-existing tools and templates.",
  "Client grants back a perpetual, irrevocable licence.",
  "",
  "5. Additional Work. Designer will make reasonable changes at no additional cost.",
  "",
  "6. Restrictions. Designer shall not, during the term and for two years after, engage in any business",
  "that competes with Client (non-compete), and shall provide services on an exclusive basis.",
  "",
  "7. Liability. Designer shall indemnify and hold harmless Client against any claims, and shall be liable",
  "for all damages without limitation of liability.",
  "",
  "8. Term. This agreement shall automatically renew for successive one-year terms.",
  "Client may terminate this agreement at any time for convenience.",
  "",
  "9. Governing Law. This agreement is governed by the laws of the State of Delaware and the parties",
  "submit to the exclusive jurisdiction of its courts.",
].join("\n");

/* ------------------------------------------------------------------ *
 * Reading the contract
 * ------------------------------------------------------------------ */

function escapeRe(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Split pasted text into blocks. A blank line starts one, and so does a
 * numbered clause that begins on a new line.
 */
function blocksOf(text) {
  const blocks = [];
  text
    .split(/\n{2,}/)
    .flatMap((chunk) => chunk.split(/\n(?=\s*\d+[.)]\s)/))
    .forEach((chunk) => {
      const body = chunk.trim();
      if (body) blocks.push({ text: body, marks: [], hits: [] });
    });

  let cursor = 0;
  blocks.forEach((block) => {
    block.offset = cursor;
    cursor += block.text.length + 2; // "\n\n" between blocks
  });
  return { blocks, joined: blocks.map((block) => block.text).join("\n\n") };
}

/**
 * Choose the sentence a highlight should actually cover: the one the found
 * window overlaps most. A built-in check quotes a padded snippet, so its window
 * can start mid-word and spill into the neighbouring sentence; picking the
 * best-overlapping sentence turns that into a phrase a person would quote.
 * Falls back to the raw window if the sentence turns out to be enormous.
 */
function snapToSentence(text, start, end) {
  const bounds = [];
  const boundary = /[.;]\s|\n/g;
  let found;
  while ((found = boundary.exec(text)) !== null) bounds.push(found.index + found[0].length);

  const starts = [0, ...bounds];
  let best = null;
  starts.forEach((from, index) => {
    const to = index + 1 < starts.length ? starts[index + 1] : text.length;
    const overlap = Math.min(end, to) - Math.max(start, from);
    if (overlap > 0 && (!best || overlap > best.overlap)) best = { overlap, from, to };
  });
  if (!best || best.to - best.from > 340) return [start, end];

  let { from, to } = best;
  while (from < to && /\s/.test(text[from])) from += 1;
  while (to > from && /\s/.test(text[to - 1])) to -= 1;
  return [from, to];
}

/**
 * Find where a finding's quote sits in the contract.
 *
 * Tries the longest run of quote words first, so a short accidental match never
 * beats a long deliberate one. Returns null when nothing convincing matches,
 * and the finding is shown as a loose note instead.
 */
function placeFinding(blocks, joined, quote) {
  const tokens = quote.replace(/…/g, " ").split(/\s+/).filter(Boolean);
  const longest = Math.min(tokens.length, 16);

  for (let size = longest; size >= 3; size -= 1) {
    for (let start = 0; start + size <= tokens.length; start += 1) {
      const pattern = tokens.slice(start, start + size).map(escapeRe).join("\\s+");
      const match = new RegExp(pattern).exec(joined);
      if (!match || match[0].length < 10) continue;

      const block = blocks.find(
        (candidate) =>
          match.index >= candidate.offset &&
          match.index + match[0].length <= candidate.offset + candidate.text.length,
      );
      if (!block) continue; // a match spanning two blocks is padded snippet, not a clause

      const from = match.index - block.offset;
      const [hitStart, hitEnd] = snapToSentence(block.text, from, from + match[0].length);
      return { block, start: hitStart, end: hitEnd };
    }
  }
  return null;
}

/** Merge overlapping highlights so marks never nest. */
function mergeHits(hits) {
  const merged = [];
  [...hits]
    .sort((a, b) => a[0] - b[0])
    .forEach(([start, end]) => {
      const last = merged[merged.length - 1];
      if (last && start <= last[1]) last[1] = Math.max(last[1], end);
      else merged.push([start, end]);
    });
  return merged;
}

/** Clause text with its trigger words underlined. */
function paint(text, ranges) {
  const fragment = document.createDocumentFragment();
  let cursor = 0;
  ranges.forEach(([start, end]) => {
    if (start > cursor) fragment.append(text.slice(cursor, start));
    const hit = document.createElement("mark");
    hit.className = "hit";
    hit.textContent = text.slice(start, end);
    fragment.append(hit);
    cursor = end;
  });
  fragment.append(text.slice(cursor));
  return fragment;
}

/** Trim the ellipses a padded snippet arrives with, keeping one if truncated. */
function tidyQuote(quote) {
  const raw = quote.trim();
  const leading = raw.startsWith("…") || raw.startsWith("...");
  const trailing = raw.endsWith("…") || raw.endsWith("...");
  let tokens = raw
    .replace(/^[.…\s]+/, "")
    .replace(/[.…\s]+$/, "")
    .split(/\s+/)
    .filter(Boolean);
  if (leading && tokens.length > 3) tokens = tokens.slice(1);
  if (trailing && tokens.length > 3) tokens = tokens.slice(0, -1);
  return (leading ? "…" : "") + tokens.join(" ") + (trailing ? "…" : "");
}

function looksLikeHeading(text) {
  return text.length < 70 && text.split(/\s+/).length <= 9 && !/[.!?]$/.test(text) && !/\d/.test(text);
}

/* ------------------------------------------------------------------ *
 * Building the page
 * ------------------------------------------------------------------ */

function markCard(finding, withQuote) {
  const card = document.createElement("article");
  card.className = "mark risk-" + finding.risk;

  const line = document.createElement("p");
  line.className = "mark-line";
  line.textContent = RISK_LABEL[finding.risk] || finding.risk;
  if (finding.category) {
    const category = document.createElement("span");
    category.className = "mark-cat";
    category.textContent = finding.category;
    line.append(" ", category);
  }

  const title = document.createElement("h3");
  title.className = "mark-title";
  title.textContent = finding.clause;
  card.append(line, title);

  if (withQuote && finding.quote) {
    const quote = document.createElement("blockquote");
    quote.className = "mark-quote";
    quote.textContent = tidyQuote(finding.quote);
    card.append(quote);
  }
  if (finding.why) {
    const why = document.createElement("p");
    why.className = "mark-why";
    why.textContent = finding.why;
    card.append(why);
  }
  if (finding.counter) {
    const ask = document.createElement("p");
    ask.className = "mark-ask";
    const label = document.createElement("strong");
    label.textContent = "Ask for: ";
    ask.append(label, document.createTextNode(finding.counter));
    card.append(ask);
  }
  return card;
}

function renderHeader(report) {
  const verdict = $("verdict");
  verdict.replaceChildren("Overall risk: ");
  const word = document.createElement("strong");
  word.className = "risk-word risk-" + report.overall_risk;
  word.textContent = report.overall_risk;
  verdict.append(word);

  const counts = report.counts;
  let tally =
    `${counts.high} high, ${counts.medium} medium, ${counts.low} low.`;
  if (report.findings.length) {
    const fromRules = report.findings.filter((f) => f.source === "rule").length;
    const fromModel = report.findings.length - fromRules;
    tally += ` The built-in checks found ${fromRules}`;
    tally += fromModel
      ? `; the local model added ${fromModel}.`
      : "; the local model had nothing to add.";
  }
  $("tally").textContent = tally;
  $("summary").textContent = report.summary || "";
  $("engine").textContent = report.model
    ? `Read locally with ${report.model}.`
    : "Read with the built-in checks only; no model was involved.";
}

function renderWarnings(report) {
  const box = $("warnings");
  box.replaceChildren();
  (report.warnings || []).forEach((text) => {
    const p = document.createElement("p");
    p.className = "warning";
    p.textContent = text;
    box.appendChild(p);
  });
}

function renderDocument(contract, report) {
  const list = $("document");
  list.replaceChildren();

  const { blocks, joined } = blocksOf(contract);
  const loose = [];

  report.findings.forEach((finding) => {
    const place = finding.quote ? placeFinding(blocks, joined, finding.quote) : null;
    if (place) {
      place.block.marks.push(finding);
      place.block.hits.push([place.start, place.end]);
    } else {
      loose.push(finding);
    }
  });

  blocks.forEach((block) => {
    const item = document.createElement("li");
    item.className = "clause";
    if (looksLikeHeading(block.text) && !block.marks.length) item.classList.add("clause-heading");

    const text = document.createElement("div");
    text.className = "clause-text";
    const para = document.createElement("p");
    // Hard line breaks in a pasted contract are usually just wrapping. Collapse
    // them for display; the swap is length-preserving, so the hit ranges hold.
    para.append(paint(block.text.replace(/\n/g, " "), mergeHits(block.hits)));
    text.append(para);
    item.append(text);

    if (block.marks.length) {
      item.classList.add(
        "risk-" +
          block.marks.reduce(
            (worst, finding) => (RISK_ORDER[finding.risk] < RISK_ORDER[worst] ? finding.risk : worst),
            "low",
          ),
      );
      const aside = document.createElement("aside");
      aside.className = "marks";
      block.marks.forEach((finding) => aside.append(markCard(finding, false)));
      item.append(aside);
    }
    list.append(item);
  });

  const section = $("loose");
  const marks = $("loose-marks");
  marks.replaceChildren();
  loose.forEach((finding) => marks.append(markCard(finding, true)));
  section.hidden = loose.length === 0;
}

function render(contract, report) {
  $("report-empty").hidden = true;
  $("report-body").hidden = false;

  renderHeader(report);
  renderWarnings(report);
  renderDocument(contract, report);

  const letter = $("letter");
  if (report.email) {
    letter.hidden = false;
    $("email").textContent = report.email;
  } else {
    letter.hidden = true;
    $("email").textContent = "";
  }
}

function reset() {
  $("report-empty").hidden = false;
  $("report-body").hidden = true;
  $("letter").hidden = true;
  $("document").replaceChildren();
  $("loose-marks").replaceChildren();
  $("email").textContent = "";
  $("warnings").replaceChildren();
}

function setStatus(text) {
  $("status").textContent = text || "";
}

/* ------------------------------------------------------------------ *
 * Doing the work
 * ------------------------------------------------------------------ */

const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

async function analyseContract() {
  const contract = $("contract").value.trim();
  if (!contract) {
    setStatus("Paste a contract first.");
    $("contract").focus();
    return;
  }

  const button = $("analyze");
  button.disabled = true;
  $("report").setAttribute("aria-busy", "true");
  setStatus("Reading the contract on this machine. A small model can take a minute.");

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: contract, email: $("want-email").checked }),
    });
    const data = await response.json();
    if (!response.ok) {
      setStatus(data.error || "That did not work. Check the contract text and try again.");
      return;
    }

    render(contract, data);
    setStatus("Done. Nothing left this computer.");

    const report = $("report");
    if (report.getBoundingClientRect().top > window.innerHeight * 0.5) {
      report.scrollIntoView({ behavior: REDUCED ? "auto" : "smooth", block: "start" });
    }
  } catch (error) {
    setStatus("Redline is not answering: " + error.message);
  } finally {
    button.disabled = false;
    $("report").removeAttribute("aria-busy");
  }
}

$("analyze").addEventListener("click", analyseContract);

$("sample").addEventListener("click", () => {
  $("contract").value = SAMPLE;
  reset();
  setStatus("Sample contract loaded. Choose Analyse contract.");
  $("contract").focus();
});

$("clear").addEventListener("click", () => {
  $("contract").value = "";
  reset();
  setStatus("");
  $("contract").focus();
});

$("copy-email").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText($("email").textContent);
    setStatus("Note copied to the clipboard.");
  } catch {
    setStatus("Copying needs permission here — select the text and copy it manually.");
  }
});
