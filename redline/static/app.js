"use strict";

const $ = (id) => document.getElementById(id);

const RISK_LABEL = { high: "High", medium: "Medium", low: "Low" };

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

function setStatus(text) {
  $("status").textContent = text || "";
}

function note(label, text) {
  const p = document.createElement("p");
  p.className = "finding-note";
  const strong = document.createElement("strong");
  strong.textContent = label + ": ";
  p.append(strong, document.createTextNode(text));
  return p;
}

function render(report) {
  $("empty").hidden = true;
  $("result").hidden = false;

  const score = $("score");
  score.className = "score risk-" + report.overall_risk;
  score.textContent = "Overall risk: " + report.overall_risk.toUpperCase();

  $("summary").textContent = report.summary || "";

  const counts = $("counts");
  counts.replaceChildren();
  ["high", "medium", "low"].forEach((level) => {
    const chip = document.createElement("span");
    chip.className = "chip risk-" + level;
    chip.textContent = report.counts[level] + " " + RISK_LABEL[level];
    counts.appendChild(chip);
  });

  const warnings = $("warnings");
  warnings.replaceChildren();
  (report.warnings || []).forEach((text) => {
    const p = document.createElement("p");
    p.className = "warning";
    p.textContent = text;
    warnings.appendChild(p);
  });

  const list = $("findings");
  list.replaceChildren();
  report.findings.forEach((finding) => {
    const li = document.createElement("li");
    li.className = "finding risk-" + finding.risk;

    const head = document.createElement("div");
    head.className = "finding-head";
    const title = document.createElement("h3");
    title.textContent = finding.clause;
    const badge = document.createElement("span");
    badge.className = "badge risk-" + finding.risk;
    badge.textContent = finding.risk;
    const category = document.createElement("span");
    category.className = "category";
    category.textContent = finding.category;
    head.append(title, badge, category);
    li.appendChild(head);

    if (finding.quote) {
      const quote = document.createElement("blockquote");
      quote.textContent = finding.quote;
      li.appendChild(quote);
    }
    if (finding.why) {
      li.appendChild(note("Why it matters", finding.why));
    }
    if (finding.counter) {
      li.appendChild(note("Ask for", finding.counter));
    }
    list.appendChild(li);
  });

  const emailBlock = $("email-block");
  if (report.email) {
    emailBlock.hidden = false;
    $("email").textContent = report.email;
  } else {
    emailBlock.hidden = true;
  }
}

async function analyzeContract() {
  const text = $("contract").value.trim();
  if (!text) {
    setStatus("Paste a contract first.");
    return;
  }

  const button = $("analyze");
  button.disabled = true;
  setStatus("Reading the contract with the local model… this can take a moment on a laptop.");

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text, email: $("want-email").checked }),
    });
    const data = await response.json();
    if (!response.ok) {
      setStatus(data.error || "Something went wrong.");
      return;
    }
    render(data);
    setStatus("Done. Nothing left this machine.");
  } catch (error) {
    setStatus("Could not reach Redline: " + error.message);
  } finally {
    button.disabled = false;
  }
}

$("analyze").addEventListener("click", analyzeContract);
$("sample").addEventListener("click", () => {
  $("contract").value = SAMPLE;
  setStatus("Sample contract loaded.");
});
$("clear").addEventListener("click", () => {
  $("contract").value = "";
  setStatus("");
});
$("copy-email").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText($("email").textContent);
    setStatus("Email copied to clipboard.");
  } catch {
    setStatus("Copy failed — select the text manually.");
  }
});
