# Redline interface — design notes

Written before the code, following the `frontend-design` skill: a design plan, then a review of
that plan against the generic defaults, then the build.

## The brief

- **Product:** Redline, a local-first contract red-flag scanner for freelancers.
- **Who uses it:** a freelance designer, developer, or writer holding a client contract they cannot
  afford to have a lawyer read. They are mildly anxious, it is late, and they want two things:
  *what is in here*, and *what do I say about it*.
- **The subject's world:** the printed contract, the clause number, the red pen, the margin note,
  the tracked change. Not a dashboard.

## Colour — the desk, the paper, the pen

| Token | Value | Role |
|---|---|---|
| `--stock` | `#e6e6e0` | the desk: a cool grey-green stock, deliberately not warm cream |
| `--sheet` | `#f7f7f4` | the paper a report is printed on |
| `--sheet-2` | `#fdfdfb` | the page you type into |
| `--ink` | `#191b21` | printed text |
| `--rule` | `#cdcdc6` | hairlines, and nothing else |
| `--red` | `#bf2f26` | the correction pen: the wordmark rule, high risk, the underline on trigger words |
| `--amber` | `#8f6412` | medium risk |
| `--green` | `#2f6a4c` | low risk |
| `--hit` | `#f6e4e0` | the faint wash under the marked words |

One accent. Red means *this is a risk*, so red is used for nothing else except the wordmark rule.

## Type

Two families, clearly distinct, doing different jobs:

- **The contract** is set in a text serif (`Iowan Old Style` → `Palatino Linotype` → `Georgia`),
  because the contract is a document. Line length is capped under 80 characters.
- **Redline's own voice** (annotations, buttons, chrome) is a system grotesque, so the margin notes
  are visibly the tool speaking, not the contract.

No webfonts and no CDN. A page that claims the contract never leaves the machine cannot phone a
font server on load — offline is part of the design, not a fallback.

## Layout — the contract is the interface

```
+-------------------------------------------------------------------------+
|  Redline                                 runs on this machine           |
|  ======                                                                 |
+-------------------------------------------------------------------------+
|  Paste a client contract. See what it asks of you.                      |
|  +-------------------------------------------------------------------+  |
|  | 1. Scope. Designer will provide design services as requested by     |  |
|  |    Client from time to time. Client may request unlimited revisions |  |
|  |    until Client is satisfied.                                       |  |
|  +-------------------------------------------------------------------+  |
|  [ Analyse contract ]   [ ] also draft a note to the client   Clear      |
+-------------------------------------------------------------------------+
|  Overall risk: high            <- report sheet                          |
|  9 high, 4 medium, 1 low. The built-in checks found 10; the model added 5.|
|                                                                          |
|  1. Scope. Designer will provide   |  High risk  Scope                    |
|     design services as requested   |  Unlimited revisions                 |
|     by Client from time to time.   |  An open-ended revision loop turns   |
|     Client may request [unlimited  |  a fixed-price project into unpaid   |
|     revisions] until Client is     |  work.                               |
|     satisfied.                     |  Ask for: cap it ...                 |
+-------------------------------------------------------------------------+
```

Findings are marginalia attached to the clause that triggered them, not a grid of cards. The exact
trigger words are underlined in red *inside* the clause, so the evidence and the advice sit
together. Below about 62rem the margin folds under its clause.

## Principles

1. The contract is the interface: every finding sits beside the clause it marks.
2. One accent, reserved for risk. Red is not decoration.
3. No page-load animation except the marks settling in once, and nothing at all under
   `prefers-reduced-motion`.
4. Works offline, prints like a marked-up document, and reads correctly at 320px.
5. Risk is always stated in words as well as colour.

## Defaults this plan rejects

Run against the common AI-generated design tells, and changed:

- **Warm cream + serif display + terracotta** → cool grey-green stock, and the serif is used for the
  document's own text rather than as a display conceit.
- **SaaS card kit** — identical rounded cards, one radius, one soft shadow → removed. Findings are
  marginalia in a document; there is no card grid.
- **Template chrome** — tracked-out all-caps eyebrows, `A · B · C` meta strings, a monospace face for
  small labels, `→` on every action → removed. Risk reads as the words "High risk"; counts read as
  a sentence.
- **Numbered `01 / 02 / 03` markers** → not added. Clause numbers come from the contract itself;
  inventing decoration numbers would be a lie about the content.
- **Rounded everything** → a 3px radius, used only on things you can actually click.

## Quality floor

- Responsive to 320px; keyboard focus visible on every control; skip link to the contract.
- `role="status"` on the progress line so a screen reader hears the analysis state.
- Empty, loading, model-unavailable, and network-failure states all say what to do next.
- The built-in checks still produce a full report when the model is missing, and the page says so.
