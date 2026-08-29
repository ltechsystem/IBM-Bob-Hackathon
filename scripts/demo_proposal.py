"""
scripts/demo_proposal.py — Demo the proposal CLI without running the full pipeline.

Feeds a hardcoded Classification through present_proposal() so the review
layer UI can be developed, tested, and rehearsed independently.

Usage
-----
# Demo the stale test proposal (default):
    python scripts/demo_proposal.py

# Demo other scenarios:
    python scripts/demo_proposal.py --scenario regression
    python scripts/demo_proposal.py --scenario new_coverage
    python scripts/demo_proposal.py --scenario uncertain

# Use a custom member name:
    python scripts/demo_proposal.py --scenario stale --member MYMODULE
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from sentinel.models import Classification
from sentinel.proposals import present_proposal

SCENARIOS: dict[str, Classification] = {
    "stale": Classification(
        verdict="STALE",
        confidence=0.92,
        rationale=(
            "The rounding rule changed from 2 decimal places to 1 decimal place. "
            "The test still asserts the old value 9.99 — it needs updating to 10.0."
        ),
        proposed_patch="""\
--- ORDCALCT (previous)
+++ ORDCALCT (proposed)
@@ -12,7 +12,7 @@
 dcl-proc test_rounding;
   dcl-s result packed(11:2);
   result = calcTotal(3: 3.33: 0);
-  iEqual(9.99: result);
+  iEqual(10.0: result);
 end-proc;
""",
    ),
    "regression": Classification(
        verdict="REGRESSION",
        confidence=0.95,
        rationale=(
            "The basic calculation test expects 50.00 but the change introduced "
            "an off-by-one error that produces 49.00. This is a genuine bug — "
            "fix the source code, not the test."
        ),
        proposed_patch="",
    ),
    "new_coverage": Classification(
        verdict="NEW_COVERAGE_NEEDED",
        confidence=0.88,
        rationale=(
            "A new premium discount branch (disc > 20) was added with no "
            "corresponding test procedure. A new test should be written."
        ),
        proposed_patch="""\
--- ORDCALCT (previous)
+++ ORDCALCT (proposed)
@@ -20,3 +20,10 @@
 dcl-proc test_rounding;
   dcl-s result packed(11:2);
   result = calcTotal(3: 3.33: 0);
   iEqual(9.99: result);
 end-proc;
+
+dcl-proc test_premiumDiscount;
+  dcl-s result packed(11:2);
+  result = calcTotal(10: 5.00: 25);
+  iEqual(37.50: result);
+end-proc;
""",
    ),
    "uncertain": Classification(
        verdict="UNCERTAIN",
        confidence=0.45,
        rationale=(
            "The change modified both the rounding logic and the discount tier "
            "simultaneously. It is unclear whether the test failure reflects "
            "stale assertions or a genuine regression — human review needed."
        ),
        proposed_patch="",
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo the Sentinel proposal CLI")
    parser.add_argument(
        "--scenario",
        default="stale",
        choices=list(SCENARIOS.keys()),
        help="Classification scenario to demo (default: stale)",
    )
    parser.add_argument(
        "--member",
        default="ORDCALC",
        help="Source member name shown in output (default: ORDCALC)",
    )
    args = parser.parse_args()

    classification = SCENARIOS[args.scenario]
    outcome = present_proposal(classification, args.member)
    print(f"\nOutcome: {outcome}")


if __name__ == "__main__":
    main()
