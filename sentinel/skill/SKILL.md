---
name: test-failure-classifier
description: >
  Classifies a failing RPGUnit test as STALE_TEST, REGRESSION, or UNCERTAIN
  after a legacy RPG code change. Bob is the sole reasoning engine. The backend
  provides evidence; Bob submits a structured ClassificationResult.
---

# Test Failure Classifier

You are classifying a failing RPGUnit test to determine whether it represents:
- A **stale test** — the implementation changed a behavior intentionally and
  the test needs updating to match the new intended contract
- A **regression** — the implementation broke a valid contract; the test is
  correct and the code must be fixed
- An **uncertain case** — evidence is insufficient to decide without human input

This classification is the core safety mechanism of the test maintenance system.
Read every rule in this skill before producing output. Do not skip sections.

---

## Preliminary: what "needs_human_review" means

`needs_human_review: true` means the workflow requires explicit human attention
before proceeding. The exact reason depends on classification:

- **REGRESSION** — always true. Implementation problems must be surfaced to a
  developer and must never be silently repaired by changing tests, even when
  Bob's classification confidence is high. The developer must see this.
- **UNCERTAIN** — always true. Bob cannot decide confidently. A human must judge.
- **STALE_TEST** — may be false when classification is well-supported by explicit
  behavior-authorizing developer intent. However, when STALE_TEST is inferred
  from the diff alone without explicit intent, prefer `needs_human_review: true`
  as a conservative safeguard.

`needs_human_review` does NOT control whether changes are applied.
Every proposed test or code diff — regardless of classification, confidence, or
the value of `needs_human_review` — requires explicit developer Accept or Reject
before anything is applied. Nothing auto-commits. Nothing auto-applies.
The developer decides everything, always.

---

## Step 1 — Retrieve evidence

Call the evidence endpoint:

```
POST http://localhost:8000/evidence
Content-Type: application/json

{
  "file": "<file>",
  "test_name": "<test_name>",
  "demo_case": "<stale_test|regression|uncertain>"   ← omit in live mode
}
```

You will receive an EvidencePayload. Inspect every field before reasoning.
Do not classify until you have reviewed all available evidence.

---

## Step 2 — Reason through these questions in order

### Q1 — Is there a material diff?

Does `diff` show a change to the procedure under test?

- No meaningful diff → likely environmental failure.
  → UNCERTAIN. Reason: "No code change detected. Failure may be environmental."
- Diff present → continue to Q2.

### Q2 — Does the diff directly explain the assertion gap?

Compare `expected` vs `actual` against what the diff changed.

- Diff explains the gap (e.g., a constant changed from 0.10 to 0.20 and
  the test still asserts the result of the 0.10 calculation) → continue to Q3.
- Diff does NOT explain the gap (unrelated procedure changed, or the
  behavioral delta is larger than the diff accounts for) → UNCERTAIN.
  Reason: "Diff does not explain the assertion gap."

### Q3 — Was the behavioral change intentional?

This is the classification decision. Apply the rules below in order.

#### Rule A — Behavior-authorizing intent (strongly supports STALE_TEST)

`developer_intent` supports STALE_TEST ONLY when it explicitly authorizes
the observed change in externally observable behavior.

Examples that qualify:
- "Increase VIP discount from 10% to 20%"
- "Change tax calculation to apply inclusive rate"
- "Fee cap raised to $500 per account"

Examples that do NOT qualify:
- "Refactor calculateDiscount for readability"
- "Extract helper method"
- "Rename variable"
- "Clean up discount logic"
- "Performance improvement"

If `developer_intent` describes implementation-only work (refactor, cleanup,
extract, rename, restructure) but the assertion result changed, the intent does
NOT justify the behavioral change. A behavior-preserving refactor should not
change what the test asserts. If it does, weight toward REGRESSION unless
another piece of evidence explicitly explains the output difference.

When Rule A applies: → STALE_TEST, high confidence (0.85–0.97),
`needs_human_review: false` is acceptable.

When intent is implementation-only or absent: continue to Rule B.

#### Rule B — Inferred intent from the diff (use carefully)

When `developer_intent` is absent or does not authorize the behavioral change,
inspect the diff for intent signals. Be conservative.

**Signals that may support STALE_TEST (inferred, lower confidence):**
- The diff introduces a new code branch or condition that clearly adds
  new externally observable behavior (not merely restructures existing behavior)
- A business-meaningful constant is changed (e.g., a rate or threshold)
  in a way consistent with a product decision

When these signals are present: → STALE_TEST, confidence 0.65–0.79.
Prefer `needs_human_review: true` because intent is inferred, not stated.

**Structural refactors alone do NOT support STALE_TEST:**
If the diff reorganizes code (extracts a helper, renames, inlines, moves
logic) without an explicit behavioral authorization, and the test result
changed, the correct classification is REGRESSION, not STALE_TEST. The
refactor was supposed to be behavior-preserving. If it changed observable
behavior, something broke.

**Signals that support REGRESSION:**
- The diff contains an off-by-one, a wrong operator, a boundary error,
  or a stray constant change with no apparent product rationale
- `developer_intent` is absent or describes non-behavioral work
- The behavioral delta is small, localized, and consistent with an
  accidental mistake

#### Rule C — Baseline confirmation

Compare the current `test_source` against `last_passing_test`.

If the test has not changed since it last passed, it is strong evidence of the
previously accepted behavior and contract. Whether that contract is still
current depends on the change intent and other evidence:

- If explicit behavior-authorizing intent is present (Rule A), that intent
  may supersede the old contract and support STALE_TEST.
- Without such evidence, an unexplained behavioral change that breaks an
  unchanged test strengthens the case for REGRESSION. The test was accepted
  before; the change broke it; the change is the suspect.

If both the code and the test changed independently, the picture is more
complex. Lower your confidence accordingly and consider UNCERTAIN.

---

## Step 3 — Apply the confidence threshold

Score your confidence honestly based on the evidence available.

| Evidence quality                                                  | Confidence  |
|-------------------------------------------------------------------|-------------|
| Behavior-authorizing intent + diff explains gap                   | 0.85 – 0.97 |
| No intent + accidental-looking diff + test unchanged + baseline   | 0.80 – 0.92 |
| Inferred behavioral intent + diff consistent + baseline confirms  | 0.65 – 0.79 |
| Implementation-only intent + behavioral delta + ambiguous         | 0.35 – 0.55 |
| No diff, or diff does not explain the failure                     | 0.20 – 0.45 |

### Hard confidence threshold — no exceptions

**If your honest confidence is below 0.60:**
- classification MUST be UNCERTAIN
- recommended_action MUST be ASK_HUMAN
- needs_human_review MUST be true
- proposed_diff MUST be null
- Do not reason yourself into a higher confidence figure to avoid UNCERTAIN

This rule overrides everything else. There are no STALE_TEST or REGRESSION
classifications below confidence 0.60.

---

## Step 4 — Choose the recommended action

| Classification | Required action | Notes                                         |
|----------------|-----------------|-----------------------------------------------|
| STALE_TEST     | UPDATE_TEST     | Include proposed_diff showing the test change |
| REGRESSION     | FIX_CODE        | No proposed_diff. The code must be fixed.     |
| UNCERTAIN      | ASK_HUMAN       | No proposed_diff. Escalate to the developer.  |

Note on ADD_TEST: the primary responsibility of this skill is classifying
failures as STALE_TEST, REGRESSION, or UNCERTAIN. Do not expand into general
test generation during classification. If a new uncovered branch is
incidentally identified, note it in `reason`, but the recommended_action must
be UPDATE_TEST, FIX_CODE, or ASK_HUMAN as determined by the classification.

---

## Step 5 — GUARDRAILS

### The anti-regression rule — the most important rule in this skill

> If the classification is REGRESSION, you MUST NOT produce a proposed_diff
> that modifies the test assertion to match the broken behavior.
>
> The test is the contract. The broken code must be repaired.
> A proposed_diff for a REGRESSION would instruct the developer to accept
> broken behavior as correct. This is the exact failure mode this system
> exists to prevent.

If you find yourself writing a proposed_diff for a REGRESSION, stop.
Set proposed_diff to null. Set recommended_action to FIX_CODE.

### All other guardrails

- proposed_diff is null for REGRESSION — always, no exceptions
- proposed_diff is null for UNCERTAIN — you do not know enough to propose
- needs_human_review is true for REGRESSION — always, even at high confidence
- needs_human_review is true for UNCERTAIN — always
- needs_human_review is true whenever confidence < 0.60 — always
- needs_human_review is true for STALE_TEST inferred without explicit
  behavior-authorizing developer intent — conservative default
- confidence < 0.60 means UNCERTAIN + ASK_HUMAN, no exceptions
- Implementation-only developer_intent does not justify a behavioral change
- Your reason MUST cite specific evidence: field name, value, what it means
- Vague reasons such as "the code changed" or "the test failed" are not acceptable
- Nothing auto-commits or auto-applies — the developer reviews and decides everything

---

## Step 6 — Submit the result

```
POST http://localhost:8000/classification-result
Content-Type: application/json

{
  "test_name": "<must match test_name from the evidence response>",
  "classification": "STALE_TEST | REGRESSION | UNCERTAIN",
  "confidence": <0.0–1.0>,
  "reason": "<2–4 sentences citing specific evidence fields and values>",
  "recommended_action": "UPDATE_TEST | FIX_CODE | ASK_HUMAN",
  "proposed_diff": "<unified diff string, or null>",
  "needs_human_review": <true | false>
}
```

The backend validates every safety invariant. If you receive HTTP 422,
re-read the guardrails section and correct your output.
Do not retry with the same payload.

---

## Reference — valid output combinations

| Classification | confidence | recommended_action | proposed_diff | needs_human_review        |
|----------------|------------|--------------------|---------------|---------------------------|
| STALE_TEST     | ≥ 0.60     | UPDATE_TEST        | allowed       | false if intent explicit; |
|                |            |                    |               | true if inferred only     |
| REGRESSION     | ≥ 0.60     | FIX_CODE           | null (always) | true (always)             |
| UNCERTAIN      | any        | ASK_HUMAN          | null (always) | true (always)             |

No classification is valid below confidence 0.60. Below that threshold the only
valid output is UNCERTAIN + ASK_HUMAN + needs_human_review=true + proposed_diff=null.
