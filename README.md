# Decision Gate

An open-source adversarial decision system. Two models argue about a decision. A fixed rule, not a model, decides **ACT / WAIT / ABANDON**. Real outcomes later score the reasoning.

## The idea in three lines

1. **Models argue, a rule decides.** The Builder states what the decision rests on. The Adversary attacks it and rates each objection by what it does to the decision if it stays unresolved. Neither model picks the action.
2. **The review stops when arguing stops changing the answer.** A round that adds no FATAL, BLOCKING, or MATERIAL challenge closes the review. AI can always produce another objection, so the stop is a rule, not a judgment call.
3. **The gate is three lines long**, so every result says which rule fired, which challenges fired it, and exactly what would flip it.

The key question is not "have we eliminated every objection?" It is "do we know enough to take the next action responsibly?"

![The gate on a live run: ABANDON, triggered by CH-001, with the resolves_if that would move it to WAIT](docs/screenshots/003-hospital-gate.png)

*A live run, unedited: Claude Opus 5 as Builder and Adversary on "should a 300-bed hospital replace pagers with a messaging app within 12 months?" One FATAL challenge fires the rule. The ledger says what would change the answer, and that even then the answer is WAIT. [Four such runs are annotated here.](data/decisions/README.md)*

## How it works

```mermaid
flowchart TD
    D(["Decision"]) --> B["Builder<br/>states the claims the decision rests on"]
    B --> A["Adversary<br/>raises only new challenges, each rated<br/>FATAL / BLOCKING / MATERIAL / NON_BLOCKING"]
    A --> S{{"Stop rule<br/>new consequential challenge this round?"}}
    S -- "yes, and rounds remain" --> A
    S -- "no, or round limit reached" --> G{{"Gate<br/>unresolved FATAL? else unresolved BLOCKING?"}}
    G -- "FATAL" --> ABANDON(["ABANDON"])
    G -- "BLOCKING" --> WAIT(["WAIT"])
    G -- "neither" --> ACT(["ACT<br/>MATERIAL and NON_BLOCKING<br/>carried as accepted risks"])
    WAIT -. "reopen only on a declared trigger<br/>such as the evidence named in resolves_if" .-> G
    ABANDON --> O
    WAIT --> O
    ACT --> O["Outcome scoring<br/>reality later grades the claims and accepted risks"]

    classDef model fill:#fff7ed,stroke:#9a3412,color:#111827
    classDef rule fill:#111827,stroke:#111827,color:#ffffff
    classDef result fill:#f9fafb,stroke:#6b7280,color:#111827
    class B,A model
    class S,G rule
    class D,ABANDON,WAIT,ACT,O result
```

Light boxes are model output. Dark boxes are rules. The models never touch the dark boxes: they cannot end the review early, keep it going, or choose the action.

Every run produces a ledger: the decision, the claims, every challenge with its rating and its `resolves_if`, the round at which the review stopped and why, the rule that fired, and the committed action. The ledger is what gets scored later.

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
- `if_triggers_resolved`: the action the gate would return if the triggering challenges were resolved

That makes the result mechanically traceable instead of another model recommendation. Because the gate is a rule, the ledger can state what would change the answer, not just what the answer is.

## What the rule guarantees — and what it doesn't

Being precise about this matters more than the diagram.

**Guaranteed by construction**

- **Termination.** A review ends when a round adds no FATAL, BLOCKING, or MATERIAL challenge, or when the round limit is reached. No model can keep it open.
- **No model chooses the action.** ACT / WAIT / ABANDON is computed from ledger state by three lines of code. Change the code and the ledger says so (`gate: deterministic-v1`).
- **Traceability.** Every result names the rule that fired, the challenge IDs that fired it, and the counterfactual — what the gate would return if those challenges were resolved.
- **Stable reopening.** A closed review reopens only on a declared trigger aimed at a named unresolved challenge. "Someone thought of another objection" is not a trigger.

**Not guaranteed — and where the judgment still lives**

- **The materiality ratings are model output.** The Adversary decides whether a challenge is FATAL, BLOCKING, MATERIAL, or NON_BLOCKING, and those ratings are the gate's only input. The rule guarantees that the action follows from the ratings; it does not guarantee the ratings are right. That is the honest boundary of this design: the model is moved one step back from the decision, not removed from it.
- **A weak Adversary can starve the stop rule.** If it raises nothing consequential, the review closes early and the gate returns ACT on thin evidence. The round limit bounds cost, not quality.
- **Outcome scoring has no data yet.** The scorer exists; calibration needs resolved decisions with observed outcomes, which take time to accumulate.

What makes those limits tolerable is that the ledger is a document, not a verdict. Ratings are visible and editable before gating — a human can re-rate a challenge and re-run the gate, and the ledger records that they did. And the outcome scorer later grades exactly the thing the model got to decide: whether the risks it rated as acceptable were in fact realized.

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

### Demo mode

Demo mode needs no API key and never calls a model. It replays **one fixed worked example** through the real ledger, stop rule, and gate. The Builder and Adversary output is canned, so the decision field is locked to the example and the result is labeled as demo.

The example:

```text
Decision   Should we build a cardiology-focused procedure operations agent?

Builder    5 claims, e.g. "We can get the data" (DEPENDENCY) and
           "Coordination work is a real bottleneck" (ASSUMPTION)

Adversary  Round 1: 3 challenges
             CH-001 BLOCKING      Integration access is not confirmed
             CH-002 MATERIAL      The bottleneck is asserted, not measured
             CH-003 NON_BLOCKING  EHR vendor roadmaps are unknown
           Round 2: nothing new  -> review stops

Gate       WAIT   (rule: UNRESOLVED_BLOCKING, triggered by CH-001)
           If CH-001 is resolved -> ACT, carrying CH-002 and CH-003 as accepted risks
```

Stopping the review and returning WAIT is not a contradiction. The review stops because more argument cannot resolve CH-001. Only the evidence named in its `resolves_if` can, and the ledger says what the gate returns once it does.

Switch to **Live** to review your own decision with real models.

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

Live mode calls the providers with the API keys present on the machine running it. Nothing in this repository, and nothing in Demo mode, uses anyone else's account. If you host the UI for other people, host Demo mode only — Live mode on a public host means visitors spend your credits.


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

## Live runs

`data/decisions/003` through `006` are unedited live runs against real
decisions (a hospital replacing pagers, a Spark-to-DuckDB migration, a
congestion-pricing pilot, a bakery's third location), Claude Opus 5 in both
roles. [`data/decisions/README.md`](data/decisions/README.md) annotates each
one and records what the four runs show about the system, including the
uncomfortable parts: the stop rule never fired before the round limit, and
the Adversary never once rated a challenge NON_BLOCKING.

The hospital run is the one ABANDON:

```bash
decision-gate gate data/decisions/003-hospital-messaging.json
```

```text
ABANDON
Matched rule: UNRESOLVED_FATAL
Triggering challenges: CH-001
- Fatal unresolved challenge: Pagers are the out-of-band channel; the app cannot be its own fallback
If triggering challenges were resolved: WAIT
```

The last line is the counterfactual: answer the fatal argument and the
decision is still not ready, because ten BLOCKING challenges remain.

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
