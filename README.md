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
  -> DECISION-SUFFICIENCY GATE
  -> ACT / WAIT / ABANDON
  -> COMMIT
  -> REOPEN ONLY ON DECLARED TRIGGERS
  -> REAL-WORLD OUTCOME
  -> EVALUATE
```

## Current MVP

The end-to-end vertical slice now includes:

1. **Builder** decomposes a user decision into load-bearing claims.
2. **Adversary** generates only new challenges and classifies them FATAL / BLOCKING / MATERIAL / NON_BLOCKING.
3. **Bounded review** stops after a configured round limit or after a round produces no new consequential challenge.
4. **Deterministic gate** converts ledger state into ACT / WAIT / ABANDON. Models do not choose the final action.
5. **Resolution recipes** are mandatory for unresolved challenges.
6. **Controlled reopen** permits reopening only for declared triggers such as new evidence targeting an unresolved challenge.
7. **Outcome scorer** compares later human-recorded outcomes with original claims and accepted risks.
8. **Web decision map** explains the whole flow in a few seconds and lets the user download the resulting ledger.

## Run the UI

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
decision-gate-web
```

Open `http://127.0.0.1:8000`.

The default **Demo** mode requires no API key and exists only to demonstrate the UX.

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

```bash
decision-gate validate data/decisions/001-build-this-project.json
decision-gate gate data/decisions/001-build-this-project.json
decision-gate stop data/decisions/001-build-this-project.json
```

Check whether new evidence is allowed to reopen a closed review:

```bash
decision-gate reopen decision.json --trigger NEW_EVIDENCE --challenge CH-001
```

Score later outcomes:

```bash
decision-gate score decision.json outcomes.json
```

`outcomes.json` uses claim outcomes `HELD | FAILED | UNKNOWN` and risk outcomes `REALIZED | NOT_REALIZED | UNKNOWN` keyed by IDs from the ledger.

## Gate semantics

- unresolved **FATAL** -> `ABANDON`
- unresolved **BLOCKING** -> `WAIT`
- otherwise -> `ACT`, with unresolved MATERIAL / NON_BLOCKING items recorded as accepted risks

A review closes when a stopping condition fires. The existence of another possible objection is not itself a reopen trigger.

## Seed decision

`data/decisions/001-build-this-project.json` records the design evolution of Decision Gate itself:

- V1: generic adversarial-agent framework
- V2: adversarial validation spec/conformance suite
- V3: prospective adversarial decision system with explicit stopping and action

The final design-validation gate produced: **ACT — BUILD MVP**.

## Tests

```bash
python -m unittest discover -s tests -v
```

CI runs the same suite on every pull request.

## Product principle

> Challenge decisions before acting, know when more analysis has stopped being useful, commit to an action, and later let reality score the reasoning.
