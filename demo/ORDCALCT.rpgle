**FREE
// ============================================================
// ORDCALCT — RPGUnit test suite for ORDCALC
//
// Three test procedures covering the three demo scenarios:
//
//   test_basicCalc         — happy-path: qty=2, price=25.00, disc=0 → 50.00
//   test_discountApplied   — discount:   qty=1, price=10.00, disc=10 → 9.00
//   test_rounding          — rounding:   qty=3, price=3.33,  disc=0 → 9.99
//
// Run with:
//   RUCALLTST TSTPGM(MYLIB/ORDCALCT) TSTPRC(*ALL)
// ============================================================

ctl-opt nomain;

/copy QRPGLEREF,ASSERT       // RPGUnit assertion macros

// ------------------------------------------------------------
// test_basicCalc
// Verifies the simplest case: no discount, exact arithmetic.
// Expected: 2 * 25.00 = 50.00
// ------------------------------------------------------------
dcl-proc test_basicCalc export;
  dcl-s result packed(11:2);

  result = calcTotal(2: 25.00: 0);

  iEqual(50.00: result);

end-proc;

// ------------------------------------------------------------
// test_discountApplied
// Verifies a 10% discount is applied correctly.
// Expected: 1 * 10.00 * 0.90 = 9.00
// ------------------------------------------------------------
dcl-proc test_discountApplied export;
  dcl-s result packed(11:2);

  result = calcTotal(1: 10.00: 10);

  iEqual(9.00: result);

end-proc;

// ------------------------------------------------------------
// test_rounding
// Verifies rounding to 2 decimal places.
// Expected: 3 * 3.33 = 9.99  (rounds down at 2 dp)
// ------------------------------------------------------------
dcl-proc test_rounding export;
  dcl-s result packed(11:2);

  result = calcTotal(3: 3.33: 0);

  iEqual(9.99: result);

end-proc;
