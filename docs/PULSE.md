# How this dashboard reflects pulse data

This repository is the **public calling card** (`README.md` + SVG panels). It is **not** product source, not a wiki, and not a place to invent progress numbers.

The private engine (gitignored `engine/`, `scripts/`, `projects.local.conf`) regenerates the panels on a ~15 minute cadence. Operators should treat the committed SVGs as a **snapshot of the last regen**, then keep stream identity and blurbs correct in the **private registry** so the next regen does not resurrect stale copy.

## Public-safe copy (hard rule)

Public pulse / SVGs / README may **only** show calling-card info:

- stream nicknames
- public HTTPS URLs
- high-level purpose
- roadmap % already produced by the engine

Do **not** publish LAN IPs, localhost admin ports, lab-only ports, internal paths, or operator prose dumps. Keep those in the private registry only.

Pulse blurbs ellipsis-cap at **52** characters. Put the public-safe one-liner in the private stream registry so regen cannot roll it back.

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
| `ccdpc` | **CCDPC** | **Live public** CRT chat + share-as-image at `https://ccdpc.af-oprea.ro`. Pulse blurb (52-char cap): `Live CRT chat + share-as-image — ccdpc.af-oprea.ro`. Never `courage-pc` / “Courage PC” / OpenRouter BYOK. Never lab/admin/LAN ports. |
| `stellami` | stellami | Tarot kit + app. **Stripe** is the noted payments path for the store, **when accounts exist**. Do not invent GMV, conversion, or charge counts. Leave the engine blurb unless it already changed. |
| `mf2fv` | MF2FV | Honest engine purpose (PWA social deduction; public host `mf2fv.af-oprea.ro` is fine). |
| `runguard` | runguard | Honest engine purpose (RMM V1 — agents, inventory, patch, heal, mesh, EASM). |
| `ppcv` | PPCV | High-level purpose only (e.g. `Personal projects hub`). Never LAN or lab/admin ports. |
| other ids | as today | One-line purpose only. Mention Stripe/payments only on streams that actually have a store/payments path. |

Logo for regen: `assets/logos/ccdpc.svg` (cream CRT + teal screen). Drop any leftover `courage-pc` mapping in `projects.local.conf`.

If a regen restores `CCDPC — cream/teal CRT chat; Gemini + Stripe RON pa…` (or any `courage-pc` label), the private registry blurb is stale — put the public-safe CCDPC line above back into the registry before the next pulse.

## README vs regen

The ~15 minute refresh **rewrites** `README.md` cache-busters and the SVG files. Prose in `README.md` can disappear on the next pulse. **Do not** put “How the numbers get here” / “Copy that must match reality” blocks back on the public README. **This file is the tracked operator note**; it is not generated.

After a regen, grep the tree for `courage`, `Courage PC`, `courage-pc`, LAN IPs, `localhost`, and lab/admin port numbers. Confirm CCDPC still reads live public CRT chat + share-as-image at ccdpc.af-oprea.ro, Stellami is unchanged unless the engine already moved it, and PPCV has no LAN/port.

## CCDPC shipped state (qualitative)

On pulse, shipped means **100%** with all six chapters filled and **Launch** current — there is no separate “finalizat” chip. That is a roadmap state, not a metric invented here.
