import unittest
from decimal import Decimal

from app.services.units import convert_quantity, ingredient_cost_per_unit, units_compatible
from app.services.pricing import simulate_profit, suggest_price


class UnitConversionTests(unittest.TestCase):
    def test_gram_recipe_converts_to_kilogram_purchase_unit(self):
        self.assertEqual(convert_quantity(Decimal("20"), "gram", "kg"), Decimal("0.020"))

    def test_units_must_be_compatible(self):
        self.assertFalse(units_compatible("gram", "ml"))
        with self.assertRaises(ValueError):
            convert_quantity(Decimal("1"), "kg", "liter")

    def test_sugar_cost_matches_umkm_example(self):
        cost = ingredient_cost_per_unit(
            purchase_price=Decimal("20000"),
            purchase_quantity=Decimal("1"),
            recipe_quantity=Decimal("20"),
            recipe_unit="g",
            purchase_unit="kg",
            batch_yield=Decimal("1"),
        )
        self.assertEqual(cost, Decimal("400.00"))

    def test_batch_hpp_matches_example(self):
        total_cost = Decimal("100000") + Decimal("50000") + Decimal("25000")
        self.assertEqual(total_cost / Decimal("50"), Decimal("3500"))

    def test_target_margin_price_matches_example(self):
        minimum, rounded, profit = suggest_price(Decimal("10000"), Decimal("0.4"), 100)
        self.assertEqual(minimum, Decimal("16666.67"))
        self.assertEqual(rounded, Decimal("16700"))
        self.assertEqual(profit, Decimal("6700"))

    def test_profit_simulation_matches_example(self):
        revenue, cost, profit, margin = simulate_profit(Decimal("8000"), Decimal("20000"), Decimal("100"))
        self.assertEqual((revenue, cost, profit), (Decimal("2000000.00"), Decimal("800000.00"), Decimal("1200000.00")))
        self.assertEqual(margin, Decimal("0.6"))

    def test_margin_of_100_percent_is_rejected(self):
        with self.assertRaises(ValueError):
            suggest_price(Decimal("10000"), Decimal("1"), 100)


if __name__ == "__main__":
    unittest.main()
