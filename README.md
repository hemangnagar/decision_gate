# Decision Gate

An open-source adversarial decision system that challenges a decision, stops when further analysis has low value, forces an **ACT / WAIT / ABANDON** call, and later lets real outcomes score the reasoning.

## Why this exists

This project came out of a real design process: a primary model proposed an idea, an adversarial model repeatedly challenged it, and each round materially changed the design. That process was useful — until it exposed its own failure mode: an adversarial system can always generate another objection.

Decision Gate treats **stopping** as part of the reasoning protocol.

The key question is not:

> Have we eliminated every objection?

It is:

> Do we know enough to take the next action responsibly?

## Core lifecycle

```text
PROPOSAL
  -> CLAIMS / ASSUMPTIONS / DEPENDENCIES
  -> ADVERSARIAL REVIEW
  -> MATERIAL CHALLENGES
  -> EVIDENCE / RESOLUTION
  -> DECISION-SUFFICIENCY GATE
  -> ACT / WAIT / ABANDON
  -> COMMIT
  -> REAL-WORLD OUTCOME
  -> EVALUATE
```

## MVP

The first vertical slice includes:

1. Decision ledger schema represented as JSON.
2. Deterministic sufficiency gate.
3. Bounded-review termination rules.
4. Validation for unresolved items and resolution recipes.
5. A simple decision-map web UI.

The model orchestration layer is intentionally not implemented yet. The gate remains deterministic even when model-generated analysis is added later.

## Decision semantics

- **FATAL** unresolved challenge -> `ABANDON`
- **BLOCKING** unresolved challenge -> `WAIT`
- Otherwise -> `ACT`, with remaining material/non-blocking issues recorded as accepted risk where appropriate.

A review stops when a configured termination condition fires, such as maximum rounds or no new material challenges.

## Seed decision

`data/decisions/001-build-this-project.json` records the design evolution of Decision Gate itself:

- V1: generic adversarial-agent framework
- V2: adversarial validation spec/conformance suite
- V3: prospective adversarial decision ledger with explicit stopping and action

The final design-validation gate produced: **ACT — BUILD MVP**.

## Run locally

```bash
python -m decision_gate.cli validate data/decisions/001-build-this-project.json
python -m decision_gate.cli gate data/decisions/001-build-this-project.json
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

Open `web/index.html` directly in a browser for the static MVP decision-map UI.

## Product principle

> Challenge decisions before acting, know when more analysis has stopped being useful, commit to an action, and later let reality score the reasoning.
