# Decision ledgers

Two kinds of file live here.

- **001 and 002** are hand-authored seeds. They exist so the deterministic
  controls can be exercised without a model (`validate`, `gate`, `reopen`,
  `score`), and the main README walks through them.
- **003 through 006** are unedited live runs of `decision-gate review`:
  Claude Opus 5 as both Builder and Adversary, `max_rounds=3`, no `--context`
  supplied. The decision sentence is the only input the models saw. Nothing
  in these files was touched after the run, including the materiality
  ratings, which is the point: the notes below are about what the models
  actually did, not what we wish they had done.

Every ledger passes `decision-gate validate`, and `decision-gate gate <file>`
recomputes the action from the file alone.

## The four live runs

| Ledger | Decision | Wall time | Claims | Challenges | Rounds | Gate | If triggers resolved |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| [003](003-hospital-messaging.json) | Should a 300-bed community hospital replace pagers with a secure clinical messaging app within 12 months? | 4m 38s | 8 | 23 | 3 | **ABANDON** (UNRESOLVED_FATAL, CH-001) | WAIT |
| [004](004-spark-to-duckdb.json) | Should a data team migrate its nightly Spark batch jobs (2 TB/day) to DuckDB on a single large machine? | 4m 40s | 8 | 22 | 3 | **WAIT** (UNRESOLVED_BLOCKING, 9 triggers) | ACT |
| [005](005-congestion-pricing.json) | Should a mid-size US city pilot downtown congestion pricing for 18 months? | 4m 59s | 8 | 26 | 3 | **WAIT** (UNRESOLVED_BLOCKING, 13 triggers) | ACT |
| [006](006-bakery-third-location.json) | Should a two-location bakery open a third location in a neighboring town before hiring a general manager? | 3m 50s | 8 | 21 | 3 | **WAIT** (UNRESOLVED_BLOCKING, 12 triggers) | ACT |

Each run is four model calls: one Builder call and three Adversary rounds.
The wall time is almost entirely model latency.

### 003 — hospital messaging: the one ABANDON

The Adversary's very first challenge is the only FATAL in all four runs, and
it is a structural argument rather than a risk: pagers run on a separate RF
network with no dependency on hospital IT, so an app that *replaces* them
removes the out-of-band channel that exists for exactly the scenarios
(ransomware, network core failure, cloud outage) in which the app itself is
down. "Replace" is a different decision from "add", and the claim set never
noticed. The gate fires `UNRESOLVED_FATAL` on that one challenge and returns
ABANDON.

The counterfactual is the useful part. `if_triggers_resolved` says WAIT, not
ACT: even with the fatal argument answered (by rescoping to a hybrid, as
CH-001's own `resolves_if` proposes), ten BLOCKING challenges remain, from
Wi-Fi in MRI Faraday cages (CH-003) to the observation that a one-way paging
network produces no delivery telemetry, so the "documented rate of missed
pages" the Builder typed as a FACT cannot actually be measured (CH-012).

Worth reading for the cross-claim reasoning: CH-013 argues the HIPAA
posture in CL-007 (content-suppressed lock-screen notifications, forced
passcode) directly erodes the latency benefit promised in CL-001. CH-017
builds on CH-006 from the previous round. The Adversary is reading its own
prior output, as the prompt asks it to, not restarting each round.

### 004 — Spark to DuckDB: the run that most resembles a real design review

The domain here is the one this repository's author knows best, so it is the
easiest to grade. The challenges are the ones an experienced reviewer would
raise: the 2 TB/day figure is logical volume, not bytes read (CH-002);
Python UDFs break vectorised execution (CH-003); the comparison baseline is
an un-optimised Spark cluster (CH-006); DuckDB's single-writer model
constrains the pipeline topology, not just the SQL (CH-019); the Spark
platform probably has other tenants, so its cost does not disappear
(CH-021). CH-004 catches a tension between two claims: "a rerun fits in the
window" and "I/O fits in the window" cannot both be comfortably true.

No FATAL, nine BLOCKING, so the gate says WAIT, and the counterfactual says
ACT once those nine are resolved. That is the shape you want from a decision
that is plausible but under-evidenced. Every BLOCKING challenge carries a
concrete `resolves_if`, and most of them are the same instruction: replay
the heaviest jobs on the candidate instance and measure.

### 005 — congestion pricing: the most challenges, the widest domain span

Twenty-six challenges across law (23 U.S.C. 301 and federal-aid tolling
restrictions, state anti-diversion clauses that may forbid the revenue
recycling the equity argument depends on, Title VI), economics (parking
prices may already dominate a $2 to $8 toll; a flat charge is regressive
against trip value), politics (no council can bind its successor, and the
pilot spans an election), and measurement (an 18-month sunset biases
elasticity downward; air-quality effects will read as null). Thirteen
BLOCKING challenges trigger WAIT.

This is also where materiality inflation is most visible. Thirteen BLOCKING
ratings out of twenty-six is a lot, and a human reviewer would probably
demote several to MATERIAL. See the observations below.

### 006 — bakery: the smallest decision, still twelve BLOCKING

The Adversary does not scale its severity down for a small business. Its
strongest move is CH-008, which inverts the Builder's sequencing argument: a
GM hired *before* expansion is the person who runs the two existing sites
while the owner opens the third, and learns the standards in calm
conditions; hired after, they arrive into a three-site mess. CH-009 then
points out the decision is framed as a binary when the dominant options
(promote a shift lead, fractional operations manager, test demand with a
wholesale account or kiosk before signing a lease) sit in between. CH-012
notes that a 9 to 12 month runway without a pre-committed kill criterion
becomes the size of the loss, not the size of the buffer.

## What the four runs show about the system

These are observations, not conclusions. Four runs with one model in both
roles is a demonstration, not a sample.

**The stop rule never fired.** All four reviews ran to `max_rounds=3` and
terminated on the round limit. Every round produced at least five
consequential challenges; the smallest final round was five, the largest
seven. With this Adversary the convergence rule ("a round adds nothing
consequential") is not what bounds the review. The budget is. That matches
the README's stated guarantee (termination is by construction) and also
shows its limit: a strong Adversary does not run out of material at three
rounds. Whether round four would have added anything decision-relevant is
exactly the question the ledger cannot answer, and a plausible next
experiment.

**Nothing was rated NON_BLOCKING.** Ninety-two challenges: 1 FATAL, 44
BLOCKING, 47 MATERIAL, 0 NON_BLOCKING. The Adversary used the top three
rungs of a four-rung scale. Since the gate reads only these ratings, WAIT
is close to guaranteed whenever this Adversary is used unedited. This is the
soft spot the README already names ("the materiality ratings are model
output") shown with numbers. The intended remedy is the one the design
provides: ratings are visible and editable before gating, and a re-rated
ledger records that it was re-rated. A stricter Adversary prompt, or a
second model that only rates, are both worth trying; neither is done here.

**No context was supplied, so the claims are archetypes.** With an empty
`--context`, the Builder produced what would need to be true for a generic
instance of each decision, and the Adversary attacked those. The challenges
are correspondingly general (they cite what is "typical" or "usual" for a
hospital or a mid-size city). Real context (this hospital's pager contract
expiry, this city's transit ridership, this team's job inventory) would let
the Builder assert specifics and the Adversary contest them.

**The challenges are domain-expert grade and they compound.** Across the
four runs the Adversary cited specific statutes, named concrete failure
mechanisms rather than categories of risk, found tensions between pairs of
claims, and in later rounds extended its own earlier challenges rather than
restating them. Reading the arguments in full is the best argument for the
tool; the ledgers are meant to be read, not just gated.

**The counterfactual is the most useful single field.** For 004, 005 and
006 it says ACT; for 003 it says WAIT. That difference is the difference
between "under-evidenced" and "the framing itself is wrong", and it is
computed, not narrated.

## Reproducing

The runs were produced on the author's machine with the author's API key.
To make your own:

```bash
decision-gate review "Your decision as a yes/no question" \
  --context "Anything specific the models should know" \
  --builder-model anthropic/claude-opus-5 \
  --adversary-model anthropic/claude-opus-5 \
  --out data/decisions/007-your-decision.json
```

Progress prints to stderr while the run is in flight. Wall time for these
four was four to five minutes each. Nothing in this repository calls a model
on anyone's behalf but the person running the command.
