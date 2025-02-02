import unittest
from estate_tax_app import calculate_estate_tax, EXEMPT_AMOUNT, FUNERAL_EXPENSE, SPOUSE_DEDUCTION_VALUE, ADULT_CHILD_DEDUCTION, PARENTS_DEDUCTION, DISABLED_DEDUCTION, OTHER_DEPENDENTS_DEDUCTION

class TestEstateTaxCalculation(unittest.TestCase):
    def test_normal_case(self):
        """
        測試一般情況：總遺產 5000 萬，僅有配偶
        """
        taxable, tax_due, deductions = calculate_estate_tax(5000, SPOUSE_DEDUCTION_VALUE, 0, 0, 0, 0)
        # 預期扣除額 = 配偶扣除額 + 喪葬費扣除額
        expected_deductions = SPOUSE_DEDUCTION_VALUE + FUNERAL_EXPENSE
        expected_taxable = max(0, 5000 - EXEMPT_AMOUNT - expected_deductions)
        self.assertEqual(taxable, expected_taxable)
        # 確保稅額不為負
        self.assertGreaterEqual(tax_due, 0)
    
    def test_invalid_input(self):
        """
        測試不合理的輸入：扣除額總和超過總遺產時應拋出 ValueError
        """
        with self.assertRaises(ValueError):
            # 此處設定直系血親數目過多，使得扣除額超過總遺產
            calculate_estate_tax(2000, SPOUSE_DEDUCTION_VALUE, 5, 0, 0, 0)

if __name__ == "__main__":
    unittest.main()

