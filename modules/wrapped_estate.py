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
    """遺產稅相關常數"""
    EXEMPT_AMOUNT: float = 1333  # 免稅額
    FUNERAL_EXPENSE: float = 138  # 喪葬費扣除額
    SPOUSE_DEDUCTION_VALUE: float = 553  # 配偶扣除額
    ADULT_CHILD_DEDUCTION: float = 56  # 每位子女扣除額
    PARENTS_DEDUCTION: float = 138  # 父母扣除額
    DISABLED_DEDUCTION: float = 693  # 重度身心障礙扣除額
    OTHER_DEPENDENTS_DEDUCTION: float = 56  # 其他撫養扣除額
    TAX_BRACKETS: List[Tuple[float, float]] = field(
        default_factory=lambda: [
            (5621, 0.1),
            (11242, 0.15),
            (float('inf'), 0.2)
        ]
    )


# ===============================
# 2. 稅務計算邏輯
# ===============================
class EstateTaxCalculator:
    """遺產稅計算器"""

    def __init__(self, constants: TaxConstants):
        self.constants = constants

    def compute_deductions(self, spouse: bool, adult_children: int, other_dependents: int,
                           disabled_people: int, parents: int) -> float:
        spouse_deduction = self.constants.SPOUSE_DEDUCTION_VALUE if spouse else 0
        total_deductions = (
            spouse_deduction +
            self.constants.FUNERAL_EXPENSE +
            (disabled_people * self.constants.DISABLED_DEDUCTION) +
            (adult_children * self.constants.ADULT_CHILD_DEDUCTION) +
            (other_dependents * self.constants.OTHER_DEPENDENTS_DEDUCTION) +
            (parents * self.constants.PARENTS_DEDUCTION)
        )
        return total_deductions

    @st.cache_data
    def calculate_estate_tax(_self, total_assets: float, spouse: bool, adult_children: int,
                             other_dependents: int, disabled_people: int, parents: int) -> Tuple[float, float, float]:
        deductions = _self.compute_deductions(spouse, adult_children, other_dependents, disabled_people, parents)
        if total_assets < _self.constants.EXEMPT_AMOUNT + deductions:
            return 0, 0, deductions
        taxable_amount = max(0, total_assets - _self.constants.EXEMPT_AMOUNT - deductions)
        tax_due = 0.0
        previous_bracket = 0
        for bracket, rate in _self.constants.TAX_BRACKETS:
            if taxable_amount > previous_bracket:
                taxable_at_rate = min(taxable_amount, bracket) - previous_bracket
                tax_due += taxable_at_rate * rate
                previous_bracket = bracket
        return taxable_amount, round(tax_due, 0), deductions


# ===============================
# 3. Streamlit 介面
# ===============================
class EstateTaxUI:
    """介面"""

    def __init__(self, calculator: EstateTaxCalculator):
        self.calculator = calculator

    def render_ui(self):
        st.set_page_config(page_title="AI秒算遺產稅", layout="wide")
        st.markdown("<h1 style='text-align: center;'>AI秒算遺產稅</h1>", unsafe_allow_html=True)
        st.selectbox("選擇適用地區", ["台灣（2025年起）"], index=0)

        # ---------------- 資產輸入 ----------------
        st.markdown("## 請輸入資產資訊")
        total_assets_input = st.number_input("總資產（萬）", min_value=1000, max_value=100000, value=5000, step=100)

        # ---------------- 家庭成員輸入 ----------------
        st.markdown("## 請輸入家庭成員數")
        has_spouse = st.checkbox("是否有配偶（扣除額 553 萬）", value=False)
        adult_children_input = st.number_input("直系血親卑親屬數（每人 56 萬）", min_value=0, max_value=10, value=0)
        parents_input = st.number_input("父母數（每人 138 萬，最多 2 人）", min_value=0, max_value=2, value=0)
        disabled_people_input = st.number_input("重度以上身心障礙者數（每人 693 萬）", min_value=0, max_value=10, value=0)
        other_dependents_input = st.number_input("受撫養之兄弟姊妹、祖父母數（每人 56 萬）", min_value=0, max_value=5, value=0)

        # ---------------- 計算基礎稅額 ----------------
        try:
            taxable_amount, tax_due, _ = self.calculator.calculate_estate_tax(
                total_assets_input, has_spouse, adult_children_input,
                other_dependents_input, disabled_people_input, parents_input
            )
        except Exception as e:
            st.error(f"計算遺產稅時發生錯誤：{e}")
            return

        st.markdown(f"## 預估遺產稅：{tax_due:,.0f} 萬元")

        # ---------------- 策略模擬 ----------------
        st.markdown("---")
        st.markdown("## 模擬試算與效益評估")

        CASE_TOTAL_ASSETS = total_assets_input
        CASE_SPOUSE = has_spouse
        CASE_ADULT_CHILDREN = adult_children_input
        CASE_PARENTS = parents_input
        CASE_DISABLED = disabled_people_input
        CASE_OTHER = other_dependents_input

        default_premium = int(math.ceil(tax_due / 10) * 10)
        if default_premium > CASE_TOTAL_ASSETS:
            default_premium = CASE_TOTAL_ASSETS
        premium_case = st.number_input("購買保險保費（萬）", min_value=0, max_value=CASE_TOTAL_ASSETS, value=default_premium, step=100)
        claim_case = st.number_input("保險理賠金（萬）", min_value=0, max_value=100000, value=int(premium_case * 1.5), step=100)
        gift_case = st.number_input("提前贈與金額（萬）", min_value=0, max_value=CASE_TOTAL_ASSETS - premium_case, value=244, step=100)

        # ---------------- 五種情境 ----------------
        # 沒有規劃
        _, tax_case_no_plan, _ = self.calculator.calculate_estate_tax(CASE_TOTAL_ASSETS, CASE_SPOUSE, CASE_ADULT_CHILDREN, CASE_OTHER, CASE_DISABLED, CASE_PARENTS)
        net_case_no_plan = CASE_TOTAL_ASSETS - tax_case_no_plan

        # 提前贈與
        effective_case_gift = CASE_TOTAL_ASSETS - gift_case
        _, tax_case_gift, _ = self.calculator.calculate_estate_tax(effective_case_gift, CASE_SPOUSE, CASE_ADULT_CHILDREN, CASE_OTHER, CASE_DISABLED, CASE_PARENTS)
        net_case_gift = effective_case_gift - tax_case_gift + gift_case

        # 購買保險
        effective_case_insurance = CASE_TOTAL_ASSETS - premium_case
        _, tax_case_insurance, _ = self.calculator.calculate_estate_tax(effective_case_insurance, CASE_SPOUSE, CASE_ADULT_CHILDREN, CASE_OTHER, CASE_DISABLED, CASE_PARENTS)
        net_case_insurance = effective_case_insurance - tax_case_insurance + claim_case

        # 贈與 + 保險（未被課稅）
        effective_case_combo_not_tax = CASE_TOTAL_ASSETS - gift_case - premium_case
        _, tax_case_combo_not_tax, _ = self.calculator.calculate_estate_tax(effective_case_combo_not_tax, CASE_SPOUSE, CASE_ADULT_CHILDREN, CASE_OTHER, CASE_DISABLED, CASE_PARENTS)
        net_case_combo_not_tax = effective_case_combo_not_tax - tax_case_combo_not_tax + claim_case + gift_case

        # 贈與 + 保險（被實質課稅）
        effective_case_combo_tax = CASE_TOTAL_ASSETS - gift_case - premium_case + claim_case
        _, tax_case_combo_tax, _ = self.calculator.calculate_estate_tax(effective_case_combo_tax, CASE_SPOUSE, CASE_ADULT_CHILDREN, CASE_OTHER, CASE_DISABLED, CASE_PARENTS)
        net_case_combo_tax = effective_case_combo_tax - tax_case_combo_tax + gift_case

        # ---------------- 結果表格 ----------------
        case_data = {
            "規劃策略": [
                "沒有規劃",
                "提前贈與",
                "購買保險",
                "提前贈與＋購買保險",
                "提前贈與＋購買保險（被實質課稅）"
            ],
            "遺產稅（萬）": [
                int(tax_case_no_plan),
                int(tax_case_gift),
                int(tax_case_insurance),
                int(tax_case_combo_not_tax),
                int(tax_case_combo_tax)
            ],
            "家人總共取得（萬）": [
                int(net_case_no_plan),
                int(net_case_gift),
                int(net_case_insurance),
                int(net_case_combo_not_tax),
                int(net_case_combo_tax)
            ]
        }
        df_case_results = pd.DataFrame(case_data)
        baseline_value = df_case_results.loc[df_case_results["規劃策略"] == "沒有規劃", "家人總共取得（萬）"].iloc[0]
        df_case_results["規劃效益"] = df_case_results["家人總共取得（萬）"] - baseline_value

        st.table(df_case_results)

        # ---------------- CSV 下載 ----------------
        csv = df_case_results.to_csv(index=False).encode("utf-8-sig")
        st.download_button("下載試算結果 CSV", csv, "estate_simulation.csv", "text/csv", key="download-csv")

        # ---------------- 視覺化 ----------------
        fig_bar_case = px.bar(
            df_case_results,
            x="規劃策略",
            y="家人總共取得（萬）",
            title="不同規劃策略下家人總共取得金額比較",
            text="家人總共取得（萬）"
        )
        fig_bar_case.update_traces(texttemplate='%{text:.0f}', textposition='outside')

        # 顯示白色文字的「規劃效益」
        baseline_case = baseline_value
        for idx, row in df_case_results.iterrows():
            if row["規劃策略"] != "沒有規劃":
                diff = row["家人總共取得（萬）"] - baseline_case
                diff_text = f"+{int(diff)}" if diff >= 0 else f"{int(diff)}"
                fig_bar_case.add_annotation(
                    x=row["規劃策略"],
                    y=row["家人總共取得（萬）"] / 2,
                    text=diff_text,
                    showarrow=False,
                    font=dict(color="white", size=16)
                )

        st.plotly_chart(fig_bar_case, use_container_width=True)


# ===============================
# 4. 包裝成 run_estate()
# ===============================
def run_estate():
    constants = TaxConstants()
    calculator = EstateTaxCalculator(constants)
    ui = EstateTaxUI(calculator)
    ui.render_ui()
