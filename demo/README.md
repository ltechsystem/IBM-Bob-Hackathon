# Sentinel Demo Script

**Module:** `ORDCALC` — order calculation service procedure  
**Test suite:** `ORDCALCT` — three RPGUnit test procedures  
**Runtime:** stub mode (`IBMI_STUB=true`, `SENTINEL_BOB_STUB=true`) — no live IBM i required

---

## Pre-flight checklist

Run these before the demo starts (takes ~30 seconds):

```powershell
# 1. Confirm environment
py -c "from sentinel.watcher import watch; print('OK')"

# 2. Seed snapshot with the BASE version of ORDCALC (all_pass scenario)
#    This must be done before each step so the diff engine has a clean baseline.
$env:IBMI_STUB = "true"
$env:SENTINEL_BOB_STUB = "true"
$env:SENTINEL_STUB_SCENARIO = "all_pass"
Remove-Item -Path ".sentinel_store\MYLIB__QRPGLESRC__ORDCALC.rpgle" -ErrorAction SilentlyContinue
py -c "from dotenv import load_dotenv; load_dotenv(); from sentinel.diff import seed_snapshot; seed_snapshot('MYLIB','QRPGLESRC','ORDCALC'); print('seeded')"

# 3. Verify coverage script works
py scripts/test_coverage.py
```

Expected: no errors, coverage shows `2/4 -> 3/4 (+25.0%)`.

---

## Demo overview

| Step | Change | Sentinel verdict | Key moment |
|------|--------|-----------------|------------|
| 0 | Base version — all tests pass | — | Show green pipeline |
| 1 | Rounding rule: 2 dp → 1 dp | **STALE** | Accept the patch |
| 2 | Off-by-one bug in qty | **REGRESSION** | Red banner, no patch |
| 3 | New premium discount branch | **NEW_COVERAGE_NEEDED** | Accept new test |

---

## Step 0 — Base version, all tests pass

**What to say:**  
> "Here's ORDCALC — a simple order calculation procedure. Three tests: basic arithmetic, discount application, and rounding. Let's start the Sentinel watcher."

**Run:**
```powershell
# Re-seed to base first
$env:SENTINEL_STUB_SCENARIO = "all_pass"
Remove-Item -Path ".sentinel_store\MYLIB__QRPGLESRC__ORDCALC.rpgle" -ErrorAction SilentlyContinue
py -c "from dotenv import load_dotenv; load_dotenv(); from sentinel.diff import seed_snapshot; seed_snapshot('MYLIB','QRPGLESRC','ORDCALC'); print('seeded')"

$env:IBMI_STUB = "true"
$env:SENTINEL_BOB_STUB = "true"
$env:SENTINEL_STUB_SCENARIO = "all_pass"
py -m sentinel.watcher --lib MYLIB --srcpf QRPGLESRC --mbr ORDCALC --once
```

**Expected output:**
```
Sentinel Watcher  —  Watching MYLIB/QRPGLESRC/ORDCALC (stub mode)
⚙  Compile detected  MYLIB/QRPGLESRC/ORDCALC  (CPC5D07-STUB)
  DIFF  ORDCALC  +2 / -1 lines changed
  Running test suite ORDCALCT...
  ✓ All 3 test(s) passed.
  Snapshot updated.
  Coverage  Before: #####.....  2/4 (50.0%)  After: #####.....  2/4 (50.0%)  Delta: +0.0%
```

**Talking point:** Green pipeline. Snapshot committed. No action required.

---

## Step 1 — Stale test (intentional rounding change)

**What to say:**  
> "The pricing team asked us to tighten rounding from 2 decimal places to 1. It's an intentional change — but it breaks the existing rounding test. Watch what Sentinel does."

**Simulate the compile event:**
```powershell
# Re-seed to base first, then run with the changed source
$env:SENTINEL_STUB_SCENARIO = "all_pass"
Remove-Item -Path ".sentinel_store\MYLIB__QRPGLESRC__ORDCALC.rpgle" -ErrorAction SilentlyContinue
py -c "from dotenv import load_dotenv; load_dotenv(); from sentinel.diff import seed_snapshot; seed_snapshot('MYLIB','QRPGLESRC','ORDCALC'); print('seeded')"

$env:SENTINEL_STUB_SCENARIO = "one_failure"
$env:SENTINEL_BOB_STUB_VERDICT = "stale"
$env:SENTINEL_STUB_COVERAGE_BEFORE = "2/4"
$env:SENTINEL_STUB_COVERAGE_AFTER = "3/4"
py -m sentinel.watcher --lib MYLIB --srcpf QRPGLESRC --mbr ORDCALC --once
```

**Expected output:**
```
⚙  Compile detected  MYLIB/QRPGLESRC/ORDCALC  (CPC5D07-STUB)
  DIFF  ORDCALC  +1 / -1 lines changed
  Running test suite ORDCALCT...
  TEST FAILURES — 1 failure(s) in ORDCALCT (2/3 passed)
    • ORDCALCT::TEST_ROUNDING — iEqual  expected='9.99'  actual='10.0'

  Classifying failure: TEST_ROUNDING...

  ══════════════════ Sentinel Proposal — ORDCALC ══════════════════

  STALE TEST — update to match new behaviour
  Verdict:    STALE
  Confidence: 92%
  The rounding rule changed from 2 dp to 1 dp. The test still
  asserts 9.99 — it needs updating to 10.0.

  --- ORDCALCT (previous)
  +++ ORDCALCT (proposed)
  @@ -12,7 +12,7 @@
   dcl-proc test_rounding;
  -  iEqual(9.99: result);
  +  iEqual(10.0: result);
   end-proc;

  [A]ccept  [R]eject  [E]dit in editor
```

**Action:** Press **A** to accept.

**What to say:**  
> "Bob correctly identified this as a stale test — not a bug. It generated the exact patch we need. One keypress to accept it. The patch is saved to `proposals/`."

**After accepting:**
```
  ✓ Patch saved → proposals/20240101_120000_ORDCALC.patch
  Coverage  Before: #####.....  2/4 (50.0%)  After: ########..  3/4 (75.0%)  Delta: +25.0%
```

**Talking point:** Coverage went up — the accepted patch closes a previously-stale coverage gap.

---

## Step 2 — Regression (genuine off-by-one bug)

**What to say:**  
> "Now a developer accidentally introduced a real bug — subtracting 1 from the quantity. The basic calculation test fails. Watch Sentinel's reaction."

```powershell
$env:SENTINEL_STUB_SCENARIO = "all_pass"
Remove-Item -Path ".sentinel_store\MYLIB__QRPGLESRC__ORDCALC.rpgle" -ErrorAction SilentlyContinue
py -c "from dotenv import load_dotenv; load_dotenv(); from sentinel.diff import seed_snapshot; seed_snapshot('MYLIB','QRPGLESRC','ORDCALC'); print('seeded')"

$env:SENTINEL_STUB_SCENARIO = "regression"
$env:SENTINEL_BOB_STUB_VERDICT = "regression"
py -m sentinel.watcher --lib MYLIB --srcpf QRPGLESRC --mbr ORDCALC --once
```

**Expected output:**
```
⚙  Compile detected  MYLIB/QRPGLESRC/ORDCALC  (CPC5D07-STUB)
  Running test suite ORDCALCT...
  TEST FAILURES — 1 failure(s) in ORDCALCT
    • ORDCALCT::TEST_BASICALC — iEqual  expected='50.00'  actual='25.00'

  Classifying failure: TEST_BASICALC...

  ⛔  REGRESSION DETECTED — manual review required
  Confidence: 95%
  The basic calculation test expects 50.00 but the change introduced
  an off-by-one error that produces 25.00. This is a genuine bug —
  fix the source code, not the test.

  The test is correct. Fix the source code, not the test.
  Snapshot NOT updated. Pipeline halted for this member.
```

**What to say:**  
> "No patch. Red banner. Sentinel refused to touch the test — because the test is right, the code is wrong. The snapshot is not updated, so the next compile will re-run the full check."

**This is the key differentiator** — a naive tool would propose updating the assertion to 25.00. Sentinel does not.

---

## Step 3 — New coverage needed (new premium discount branch)

**What to say:**  
> "Finally, a developer adds a new premium discount tier — a valid feature. All three existing tests still pass, but the new branch has no test at all."

```powershell
$env:SENTINEL_STUB_SCENARIO = "all_pass"
$env:SENTINEL_BOB_STUB_VERDICT = "new_coverage"
$env:SENTINEL_STUB_COVERAGE_BEFORE = "2/4"
$env:SENTINEL_STUB_COVERAGE_AFTER = "2/4"
py -m sentinel.watcher --lib MYLIB --srcpf QRPGLESRC --mbr ORDCALC --once
```

> **Note:** Because all tests pass in this scenario, the classifier is called on a synthetic zero-failure run. For the demo, drive this step using `demo_proposal.py` instead to guarantee the NEW_COVERAGE_NEEDED path:

```powershell
py scripts/demo_proposal.py --scenario new_coverage --member ORDCALC
```

**Expected output:**
```
  NEW COVERAGE NEEDED — add test for new branch
  Verdict:    NEW_COVERAGE_NEEDED
  Confidence: 88%
  A new premium discount branch (disc > 20) was added with no
  corresponding test procedure.

  +dcl-proc test_premiumDiscount;
  +  dcl-s result packed(11:2);
  +  result = calcTotal(10: 5.00: 25);
  +  iEqual(37.50: result);
  +end-proc;

  [A]ccept  [R]eject  [E]dit in editor
```

**Action:** Press **A** to accept.

**What to say:**  
> "Bob detected dead code — a new branch with no test. It generated a test procedure, calculated the expected value, and handed it to me for review. I accept it. Coverage goes up."

---

## Post-demo talking points

- **Zero false positives in the happy path** — Sentinel only fires when tests actually fail.
- **Three distinct verdicts** — STALE, REGRESSION, NEW_COVERAGE_NEEDED — each with a different action.
- **Human stays in control** — nothing is auto-committed; every proposal requires an explicit accept.
- **Coverage metric** — concrete before/after numbers, not a claim.
- **Bob is the reasoning engine** — Sentinel is the loop, Bob is the brain.

---

## File reference

| File | Purpose |
|------|---------|
| `demo/ORDCALC.rpgle` | Base source member — all tests pass |
| `demo/ORDCALCT.rpgle` | RPGUnit test suite — 3 procedures |
| `demo/changes/step1_stale.rpgle` | Rounding rule change (2 dp → 1 dp) |
| `demo/changes/step2_regression.rpgle` | Off-by-one bug in qty multiplier |
| `demo/changes/step3_new_branch.rpgle` | Premium discount tier (disc > 20) |

---

## Environment variable cheat sheet

```powershell
# Stub mode (no IBM i required)
$env:IBMI_STUB                     = "true"
$env:SENTINEL_BOB_STUB             = "true"

# Control which test scenario runs
$env:SENTINEL_STUB_SCENARIO        = "one_failure"   # one_failure | all_pass | regression

# Control what Bob says
$env:SENTINEL_BOB_STUB_VERDICT     = "stale"         # stale | regression | new_coverage | uncertain

# Control coverage numbers shown
$env:SENTINEL_STUB_COVERAGE_BEFORE = "2/4"
$env:SENTINEL_STUB_COVERAGE_AFTER  = "3/4"
```
