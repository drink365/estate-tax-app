import streamlit as st
import pandas as pd
import math
import plotly.express as px
from typing import Tuple, List
from dataclasses import dataclass, field

# ===============================
# 1. 常數與設定
# ===============================
@dataclass
class TaxConstants:
    EXEMPT_AMOUNT: float = 1333
    FUNERAL_EXPENSE: float = 138
    SPOUSE_DEDUCTION_VALUE: float = 553
    ADULT_CHILD_DEDUCTION: float = 56
    PARENTS_DEDUCTION: float = 138
    DISABLED_DEDUCTION: float = 693
    OTHER_DEPENDENTS_DEDUCTION: float = 56
    TAX_BRACKETS: List[Tuple[float, float]] = field(
        default_factory=lambda: [(5621, 0.1), (11242, 0.15), (float('inf'), 0.2)]
    )

# ===============================
# 2. 稅務計算
# ===============================
class EstateTaxCalculator:
    def __init__(self, constants: TaxConstants):
        self.constants = constants

    def compute_deductions(self, spouse, adult_children, other_dependents, disabled_people, parents):
        spouse_deduction = self.constants.SPOUSE_DEDUCTION_VALUE if spouse else 0
        return (
            spouse_deduction
            + self.constants.FUNERAL_EXPENSE
            + (disabled_people * self.constants.DISABLED_DEDUCTION)
            + (adult_children * self.constants.ADULT_CHILD_DEDUCTION)
            + (other_dependents * self.constants.OTHER_DEPENDENTS_DEDUCTION)
            + (parents * self.constants.PARENTS_DEDUCTION)
        )

    @st.cache_data
    def calculate_estate_tax(_self, total_assets, spouse, adult_children, other_dependents, disabled_people, parents):
        deductions = _self.compute_deductions(spouse, adult_children, other_dependents, disabled_people, parents)
        if total_assets < _self.constants.EXEMPT_AMOUNT + deductions:
            return 0, 0, deductions
        taxable_amount = max(0, total_assets - _self.constants.EXEMPT_AMOUNT - deductions)
        tax_due, prev = 0.0, 0
        for bracket, rate in _self.constants.TAX_BRACKETS:
            if taxable_amount > prev:
                taxable_at_rate = min(taxable_amount, bracket) - prev
                tax_due += taxable_at_rate * rate
                prev = bracket
        return taxable_amount, round(tax_due, 0), deductions

# ===============================
# 3. 介面
# ===============================
class EstateTaxUI:
    def __init__(self, calculator: EstateTaxCalculator):
        self.calculator = calculator

    def render_ui(self):
        st.markdown("## AI秒算遺產稅")

        # ✔ Step 1: 地區
        st.selectbox("選擇適用地區", ["台灣（2025年起）"], index=0)

        # ✔ Step 2: 資產
        st.markdown("### 請輸入資產資訊")
        total_assets_input = st.number_input("總資產（萬）", min_value=1000, max_value=100000, value=5000, step=100)

        # ✔ Step 3: 家庭成員（依你指定順序）
        st.markdown("### 請輸入家庭成員數")
        has_spouse = st.checkbox("是否有配偶（扣除額 553 萬）", value=False)
        adult_children_input = st.number_input("直系血親卑親屬數（每人 56 萬）", min_value=0, max_value=10, value=0)
        parents_input = st.number_input("父母數（每人 138 萬，最多 2 人）", min_value=0, max_value=2, value=0)
        disabled_people_input = st.number_input("重度以上身心障礙者數（每人 693 萬）", min_value=0, max_value=10, value=0)
        other_dependents_input = st.number_input("受撫養之兄弟姊妹、祖父母數（每人 56 萬）", min_value=0, max_value=5, value=0)

        # 計算
        taxable_amount, tax_due, _ = self.calculator.calculate_estate_tax(
            total_assets_input, has_spouse, adult_children_input, other_dependents_input, disabled_people_input, parents_input
        )
        st.markdown(f"### 預估遺產稅：{tax_due:,.0f} 萬元")

        # 3 欄明細
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**資產概況**")
            st.table(pd.DataFrame({"項目": ["總資產"], "金額（萬）": [int(total_assets_input)]}))
        with col2:
            st.markdown("**扣除項目**")
            df_deductions = pd.DataFrame({
                "項目": ["免稅額", "喪葬費", "配偶", "子女", "父母", "障礙", "其他"],
                "金額（萬）": [
                    self.calculator.constants.EXEMPT_AMOUNT,
                    self.calculator.constants.FUNERAL_EXPENSE,
                    self.calculator.constants.SPOUSE_DEDUCTION_VALUE if has_spouse else 0,
                    adult_children_input * self.calculator.constants.ADULT_CHILD_DEDUCTION,
                    parents_input * self.calculator.constants.PARENTS_DEDUCTION,
                    disabled_people_input * self.calculator.constants.DISABLED_DEDUCTION,
                    other_dependents_input * self.calculator.constants.OTHER_DEPENDENTS_DEDUCTION
                ]
            })
            # 安全轉整數：只轉數值欄，NaN 轉 0，避免 astype(int) 報錯
num_cols = df_deductions.select_dtypes(include=["float", "int", "int64", "float64"]).columns
df_deductions[num_cols] = df_deductions[num_cols].fillna(0).round(0).astype(int)
st.table(df_deductions)
        with col3:
            st.markdown("**稅務計算**")
            st.table(pd.DataFrame({
                "項目": ["課稅淨額", "遺產稅"],
                "金額（萬）": [int(taxable_amount), int(tax_due)]
            }))

        # 顧問式策略建議
        st.markdown("---")
        st.markdown("## 家族傳承策略建議")
        st.markdown(
            "1. **規劃保單**：透過保險預留稅源，確保資產分配順利。  \n"
            "2. **提前贈與**：利用免稅額逐年移轉財富，減少稅負。  \n"
            "3. **分散配置**：合理安排資產結構，兼顧流動性與節稅效果。"
        )

        # 策略模擬（五情境）
        st.markdown("---")
        st.markdown("## 策略模擬與效益評估")
        # 參數順序：先「提前贈與」→「保費」→「理賠金」
        gift_case = st.number_input("提前贈與金額（萬）", min_value=0, max_value=total_assets_input, value=244, step=100)
        default_premium = int((tax_due // 10) * 10)
        default_premium = min(default_premium, max(0, total_assets_input - gift_case))
        premium_case = st.number_input("購買保險保費（萬）", min_value=0, max_value=total_assets_input - gift_case, value=default_premium, step=100)
        claim_case = st.number_input("保險理賠金（萬）", min_value=0, max_value=100000, value=int(premium_case * 1.5), step=100)

        # 五情境計算
        _, tax_case_no_plan, _ = self.calculator.calculate_estate_tax(total_assets_input, has_spouse, adult_children_input, other_dependents_input, disabled_people_input, parents_input)
        net_case_no_plan = total_assets_input - tax_case_no_plan

        effective_case_gift = total_assets_input - gift_case
        _, tax_case_gift, _ = self.calculator.calculate_estate_tax(effective_case_gift, has_spouse, adult_children_input, other_dependents_input, disabled_people_input, parents_input)
        net_case_gift = effective_case_gift - tax_case_gift + gift_case

        effective_case_insurance = total_assets_input - premium_case
        _, tax_case_insurance, _ = self.calculator.calculate_estate_tax(effective_case_insurance, has_spouse, adult_children_input, other_dependents_input, disabled_people_input, parents_input)
        net_case_insurance = effective_case_insurance - tax_case_insurance + claim_case

        effective_case_combo_not_tax = total_assets_input - gift_case - premium_case
        _, tax_case_combo_not_tax, _ = self.calculator.calculate_estate_tax(effective_case_combo_not_tax, has_spouse, adult_children_input, other_dependents_input, disabled_people_input, parents_input)
        net_case_combo_not_tax = effective_case_combo_not_tax - tax_case_combo_not_tax + claim_case + gift_case

        effective_case_combo_tax = total_assets_input - gift_case - premium_case + claim_case
        _, tax_case_combo_tax, _ = self.calculator.calculate_estate_tax(effective_case_combo_tax, has_spouse, adult_children_input, other_dependents_input, disabled_people_input, parents_input)
        net_case_combo_tax = effective_case_combo_tax - tax_case_combo_tax + gift_case

        df_case = pd.DataFrame({
            "規劃策略": ["沒有規劃", "提前贈與", "購買保險", "提前贈與＋購買保險", "提前贈與＋購買保險（被實質課稅）"],
            "遺產稅（萬）": [int(tax_case_no_plan), int(tax_case_gift), int(tax_case_insurance), int(tax_case_combo_not_tax), int(tax_case_combo_tax)],
            "家人總共取得（萬）": [int(net_case_no_plan), int(net_case_gift), int(net_case_insurance), int(net_case_combo_not_tax), int(net_case_combo_tax)]
        })
        base = df_case.loc[df_case["規劃策略"] == "沒有規劃", "家人總共取得（萬）"].iloc[0]
        df_case["規劃效益"] = df_case["家人總共取得（萬）"] - base

        st.table(df_case)

        # CSV 下載
        csv = df_case.to_csv(index=False).encode("utf-8-sig")
        st.download_button("下載試算結果 CSV", csv, "estate_simulation.csv", "text/csv", key="estate-csv")

        # 圖表（白色文字顯示效益差額）
        fig = px.bar(df_case, x="規劃策略", y="家人總共取得（萬）", text="家人總共取得（萬）", title="不同策略下家人總共取得金額比較")
        fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
        for _, row in df_case.iterrows():
            if row["規劃策略"] != "沒有規劃":
                diff = row["家人總共取得（萬）"] - base
                fig.add_annotation(x=row["規劃策略"], y=row["家人總共取得（萬）"] / 2,
                                   text=f"{'+' if diff >= 0 else ''}{int(diff)}", showarrow=False,
                                   font=dict(color="white", size=16))
        st.plotly_chart(fig, config={"responsive": True}, use_container_width=True)

def run_estate():
    constants = TaxConstants()
    calculator = EstateTaxCalculator(constants)
    ui = EstateTaxUI(calculator)
    ui.render_ui()
