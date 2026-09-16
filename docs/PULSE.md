# How this dashboard reflects pulse data

This repository is the **public calling card** (`README.md` + SVG panels). It is **not** product source, not a wiki, and not a place to invent progress numbers.

The private engine (gitignored `engine/`, `scripts/`, `projects.local.conf`) regenerates the panels on a ~15 minute cadence. Operators should treat the committed SVGs as a **snapshot of the last regen**, then keep stream identity and blurbs correct in the **private registry** so the next regen does not resurrect stale copy.

## Panels

| File | What it reflects | What it does not |
| --- | --- | --- |
| `assets/pulse.svg` | Per-stream **roadmap %**, six lifecycle chapters (Start → Launch), overall ring % from those roadmaps, footer **code Δ** as % LOC over 30m / 24h / 7d / 30d | Product docs, URLs as a catalog, revenue |
| `assets/worth-panel.svg` | **CXP** and **UTIL** from each stream’s `roadmap.json`; **LOC** = non-blank source lines in local clones; **index** = `round(100 × utility ÷ (complexity + 0.5))`; language mix from those clones | Chapter bars (those live on pulse only) |
| `assets/command-center.svg` | Recent git activity: when · stream nick · action (Europe/Bucharest), last 30 days | A complete commit history |

Sort on pulse and worth is **complexity → LOC** (worth also folds utility). Striped chapter cells mean **out of track**; empty track means **pending**.

Do **not** hand-edit percentages, LOC, CXP, UTIL, language lists, or Δ values in this repo. Change the private roadmaps / clones and regen.

## Copy that must survive regen

Keep these in the private stream registry (and `projects.local.conf`) so a refresh cannot roll them back:

| Stream id | Public label | Reality to show |
| --- | --- | --- |
| `ccdpc` | **CCDPC** | **Live public** CRT chat at `https://ccdpc.af-oprea.ro` (`:8300` public / `:8301` admin). Never `courage-pc` / “Courage PC” / OpenRouter BYOK. |
| `stellami` | stellami | Tarot kit + app. **Stripe** is the noted payments path for the store, **when accounts exist**. Do not invent GMV, conversion, or charge counts. |
| other ids | as today | One-line purpose only. Mention Stripe/payments only on streams that actually have a store/payments path. |

Logo for regen: `assets/logos/ccdpc.svg` (cream CRT + teal screen). Drop any leftover `courage-pc` mapping in `projects.local.conf`.

## README vs regen

The ~15 minute refresh **rewrites** `README.md` cache-busters and the SVG files. Prose in `README.md` can disappear on the next pulse. **This file is the tracked operator note**; it is not generated.

After a regen, grep the tree for `courage`, `Courage PC`, and `courage-pc`. Confirm CCDPC still reads live public and Stellami still notes Stripe on the store path.

## CCDPC shipped state (qualitative)

On pulse, shipped means **100%** with all six chapters filled and **Launch** current — there is no separate “finalizat” chip. That is a roadmap state, not a metric invented here.
