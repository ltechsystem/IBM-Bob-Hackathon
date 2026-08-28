**FREE
// ============================================================
// ORDCALC — step3_new_branch.rpgle
//
// NEW BRANCH: premium discount tier (discount > 20).
//
// A new business rule adds a 5% loyalty bonus on top of any
// discount greater than 20%:
//
//   if discount > 20:
//     effective_discount = discount + 5
//
// All three existing tests still pass (none uses disc > 20).
// But the new branch has zero test coverage.
//
// Expected Sentinel verdict: NEW_COVERAGE_NEEDED (confidence ~0.88)
// Bob should propose a new test_premiumDiscount procedure.
// ============================================================

ctl-opt nomain;

dcl-proc calcTotal export;
  dcl-pi calcTotal packed(11:2);
    qty      int(10)      value;
    price    packed(11:2) value;
    discount packed(5:2)  value;
  end-pi;

  dcl-s subtotal        packed(11:2);
  dcl-s effectiveDisc   packed(5:2);
  dcl-s result          packed(11:2);

  subtotal = qty * price;

  effectiveDisc = discount;

  // NEW: premium loyalty bonus for high-discount orders
  if discount > 20;
    effectiveDisc = discount + 5;
  endif;

  if effectiveDisc > 0;
    subtotal = subtotal * (1 - effectiveDisc / 100);
  endif;

  result = %dech(subtotal: 11: 2);

  return result;

end-proc;
