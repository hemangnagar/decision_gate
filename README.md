# Decision Gate

An open-source adversarial decision system that challenges a decision, stops when further analysis has low value, forces an **ACT / WAIT / ABANDON** call, and later lets real outcomes score the reasoning.

## Why this exists

AI can always generate another objection. Decision Gate treats **stopping** and **commitment** as part of the reasoning protocol.

The key question is not:

> Have we eliminated every objection?

It is:

> Do we know enough to take the next action responsibly?

The models generate claims and challenges. They do **not** choose the final action.

## Core lifecycle

```text
PROPOSAL
  -> CLAIMS / ASSUMPTIONS / DEPENDENCIES
  -> ADVERSARIAL REVIEW
  -> MATERIAL CHALLENGES
  -> BOUNDED STOP
  -> DETERMINISTIC SUFFICIENCY GATE
  -> ACT / WAIT / ABANDON
  -> COMMIT
  -> REOPEN ONLY ON DECLARED TRIGGERS
  -> REAL-WORLD OUTCOME
  -> EVALUATE
```

## The deterministic control boundary

The gate is deliberately simple:

```text
IF any unresolved challenge is FATAL
    -> ABANDON
ELSE IF any unresolved challenge is BLOCKING
    -> WAIT
ELSE
    -> ACT
```

MATERIAL and NON_BLOCKING unresolved challenges are preserved as accepted risks.

Every gate result records:

- `action`
- `matched_rule`
- `triggering_challenges`
- human-readable `reasons`
- `accepted_risks`

That makes the result mechanically traceable instead of another model recommendation.

## Current MVP

The end-to-end vertical slice includes:

1. **Builder** decomposes a user decision into load-bearing claims.
2. **Adversary** generates only new challenges and classifies them FATAL / BLOCKING / MATERIAL / NON_BLOCKING.
3. **Bounded review** stops after a configured round limit or after a round produces no new consequential challenge.
4. **Deterministic gate** converts ledger state into ACT / WAIT / ABANDON. Models do not choose the final action.
5. **First-class rule trace** records which rule fired and which challenge IDs triggered it.
6. **Resolution recipes** are mandatory for unresolved challenges.
7. **Controlled reopen** permits reopening only for declared triggers such as new evidence targeting an unresolved challenge.
8. **Outcome scorer** compares later human-recorded outcomes with original claims and accepted risks.
9. **Local web UI** renders the decision map and lets the user download the resulting ledger.

## Run the UI

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
decision-gate-web
```

Open `http://127.0.0.1:8000`.

The local **Demo** mode requires no API key and exercises the same ledger and deterministic gate path with fixed providers.

## Run with real models

Decision Gate uses [LiteLLM](https://docs.litellm.ai/) as a provider-neutral adapter.

```bash
pip install -e '.[llm]'
```

Set the provider API keys required by the two model strings you choose, then select **Live models via LiteLLM** in the UI or run:

```bash
decision-gate review \
  "Should we build this product?" \
  --builder-model 'openai/<model>' \
  --adversary-model 'anthropic/<model>' \
  --out decision.json
```

Model names are intentionally user-supplied rather than pinned in the project.

## Inspect the deterministic controls

The first seed decision is intentionally rejected:

```bash
decision-gate validate data/decisions/001-generic-debate-framework.json
decision-gate gate data/decisions/001-generic-debate-framework.json
```

Expected gate:

```text
ABANDON
Matched rule: UNRESOLVED_FATAL
Triggering challenges: CH-001
```

The reframed Decision Gate proposal is a **separate decision**, not a retroactive resolution of the failed thesis:

```bash
decision-gate validate data/decisions/002-build-decision-gate.json
decision-gate gate data/decisions/002-build-decision-gate.json
```

Expected gate:

```text
ACT
Matched rule: NO_UNRESOLVED_FATAL_OR_BLOCKING
```

This distinction matters: changing the proposal creates a new ledger. A fatal challenge to Decision A cannot be “resolved” merely by turning Decision A into Decision B.

## Reopen and outcome scoring

Check whether new evidence is allowed to reopen a closed review:

```bash
decision-gate reopen decision.json --trigger NEW_EVIDENCE --challenge CH-001
```

Score later outcomes:

```bash
decision-gate score decision.json outcomes.json
```

`outcomes.json` uses claim outcomes `HELD | FAILED | UNKNOWN` and risk outcomes `REALIZED | NOT_REALIZED | UNKNOWN` keyed by IDs from the ledger.

A review closes when a stopping condition fires. The existence of another possible objection is not itself a reopen trigger.

## Tests

```bash
python -m unittest discover -s tests -v
```

CI runs the same suite on every pull request.

## Product principle

> Challenge decisions before acting, know when more analysis has stopped being useful, commit to an action, and later let reality score the reasoning.
