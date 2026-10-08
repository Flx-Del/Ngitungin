from decimal import Decimal


_UNITS: dict[str, tuple[str, Decimal]] = {
    "mg": ("mass", Decimal("0.001")),
    "g": ("mass", Decimal("1")),
    "gr": ("mass", Decimal("1")),
    "gram": ("mass", Decimal("1")),
    "grama": ("mass", Decimal("1")),
    "kg": ("mass", Decimal("1000")),
    "kilogram": ("mass", Decimal("1000")),
    "ml": ("volume", Decimal("1")),
    "mililiter": ("volume", Decimal("1")),
    "l": ("volume", Decimal("1000")),
    "liter": ("volume", Decimal("1000")),
    "cc": ("volume", Decimal("1")),
    "pcs": ("count", Decimal("1")),
    "pc": ("count", Decimal("1")),
    "buah": ("count", Decimal("1")),
    "unit": ("count", Decimal("1")),
}


def units_compatible(first: str, second: str) -> bool:
    if first.strip().casefold() == second.strip().casefold():
        return True
    a = _UNITS.get(first.strip().casefold())
    b = _UNITS.get(second.strip().casefold())
    return a is not None and b is not None and a[0] == b[0]


def convert_quantity(quantity: Decimal, from_unit: str, to_unit: str) -> Decimal:
    """Convert a quantity from the recipe unit into the material purchase unit."""
    if from_unit.strip().casefold() == to_unit.strip().casefold():
        return quantity
    source = _UNITS.get(from_unit.strip().casefold())
    target = _UNITS.get(to_unit.strip().casefold())
    if source is None or target is None or source[0] != target[0]:
        raise ValueError("Satuan bahan dan resep tidak dapat dikonversi.")
    return quantity * source[1] / target[1]


def ingredient_cost_per_unit(
    purchase_price: Decimal,
    purchase_quantity: Decimal,
    recipe_quantity: Decimal,
    recipe_unit: str,
    purchase_unit: str,
    batch_yield: Decimal,
) -> Decimal:
    if purchase_quantity <= 0 or batch_yield <= 0:
        raise ValueError("Jumlah pembelian dan hasil batch harus lebih dari nol.")
    used_in_purchase_unit = convert_quantity(recipe_quantity, recipe_unit, purchase_unit)
    return purchase_price / purchase_quantity * used_in_purchase_unit / batch_yield
