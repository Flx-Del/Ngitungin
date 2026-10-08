from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP


CENT = Decimal("0.01")


def suggest_price(cost: Decimal, target_margin: Decimal, rounding: int) -> tuple[Decimal, Decimal, Decimal]:
    if cost < 0 or not Decimal("0") <= target_margin < Decimal("1"):
        raise ValueError("HPP harus nonnegatif dan margin harus di antara 0% sampai kurang dari 100%.")
    if rounding not in (100, 500, 1000):
        raise ValueError("Pembulatan harus Rp100, Rp500, atau Rp1.000.")
    minimum = (cost / (Decimal("1") - target_margin)).quantize(CENT, rounding=ROUND_HALF_UP)
    step = Decimal(rounding)
    suggested = (minimum / step).quantize(Decimal("1"), rounding=ROUND_CEILING) * step
    return minimum, suggested, suggested - cost


def simulate_profit(cost: Decimal, selling_price: Decimal, quantity: Decimal) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    if cost < 0 or selling_price < 0 or quantity <= 0:
        raise ValueError("HPP dan harga jual tidak boleh negatif; jumlah terjual harus lebih dari nol.")
    revenue = (selling_price * quantity).quantize(CENT, rounding=ROUND_HALF_UP)
    total_cost = (cost * quantity).quantize(CENT, rounding=ROUND_HALF_UP)
    profit = revenue - total_cost
    margin = profit / revenue if revenue else Decimal("0")
    return revenue, total_cost, profit, margin
