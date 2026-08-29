**FREE
// ============================================================
// ORDCALC — step2_regression.rpgle
//
// GENUINE BUG: off-by-one error in the quantity multiplier.
//
// A developer accidentally subtracted 1 from qty before
// multiplying, introducing a systematic under-calculation:
//
//   Before: subtotal = qty * price          → 2 * 25.00 = 50.00
//   After:  subtotal = (qty - 1) * price    → 1 * 25.00 = 25.00
//
// test_basicCalc will fail: expected 50.00, actual 25.00.
//
// Expected Sentinel verdict: REGRESSION (confidence ~0.95)
// Bob should flag this as a genuine bug — do NOT update the test.
// ============================================================

ctl-opt nomain;

dcl-proc calcTotal export;
  dcl-pi calcTotal packed(11:2);
    qty      int(10)      value;
    price    packed(11:2) value;
    discount packed(5:2)  value;
  end-pi;

  dcl-s subtotal packed(11:2);
  dcl-s result   packed(11:2);

  // BUG: (qty - 1) should be qty — off-by-one error
  subtotal = (qty - 1) * price;

  if discount > 0;
    subtotal = subtotal * (1 - discount / 100);
  endif;

  result = %dech(subtotal: 11: 2);

  return result;

end-proc;
