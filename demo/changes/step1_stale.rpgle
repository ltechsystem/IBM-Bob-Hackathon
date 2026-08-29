**FREE
// ============================================================
// ORDCALC — step1_stale.rpgle
//
// INTENTIONAL CHANGE: rounding rule tightened from 2 dp to 1 dp.
//
// This is a deliberate business-logic update requested by the
// pricing team.  The change is correct — but it makes the
// existing test_rounding assertion stale:
//
//   Before: iEqual(9.99: result)   ← old 2-dp rounding
//   After:  iEqual(10.0: result)   ← new 1-dp rounding
//
// Expected Sentinel verdict: STALE (confidence ~0.92)
// Bob should propose updating the assertion from 9.99 to 10.0.
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

  subtotal = qty * price;

  if discount > 0;
    subtotal = subtotal * (1 - discount / 100);
  endif;

  // CHANGED: round to 1 decimal place (was 2)
  result = %dech(subtotal: 11: 1);

  return result;

end-proc;
