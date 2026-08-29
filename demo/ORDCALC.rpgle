**FREE
// ============================================================
// ORDCALC — Order calculation service procedure
//
// calcTotal(qty: price: discount) -> total
//
//   qty      — integer quantity
//   price    — unit price  (packed 11:2)
//   discount — discount %  (packed 5:2)  0 = no discount
//
// Business rules (base version):
//   1. subtotal = qty * price
//   2. if discount > 0: subtotal = subtotal * (1 - discount/100)
//   3. round to 2 decimal places
//
// Test suite: ORDCALCT
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

  // Round to 2 decimal places
  result = %dech(subtotal: 11: 2);

  return result;

end-proc;
