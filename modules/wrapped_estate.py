import streamlit as st
import pandas as pd
import math
import plotly.express as px
from typing import Tuple, List
from datetime import datetime
import time
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
        """計算總扣除額"""
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
        """計算遺產稅"""
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
# 3. 登入驗證
# ===============================
def check_credentials(input_username: str, input_password: str) -> (bool, str):
    """檢查使用者登入憑證"""
    authorized_users = st.secrets["authorized_users"]
    if input_username in authorized_users:
        user_info = authorized_users[input_username]
        if input_password == user_info["password"]:
            start_date = datetime.strptime(user_info["start_date"], "%Y-%m-%d")
            end_date = datetime.strptime(user_info["end_date"], "%Y-%m-%d")
            today = datetime.today()
            if start_date <= today <= end_date:
                return True, user_info["name"]
            else:
                st.error("您的使用權限尚未啟用或已過期")
                return False, ""
        else:
            st.error("密碼錯誤")
            return False, ""
    else:
        st.error("查無此使用者")
        return False, ""


# ===============================
# 4. Streamlit 介面
# ===============================
class EstateTaxUI:
    """介面"""

    def __init__(self, calculator: EstateTaxCalculator):
        self.calculator = calculator

    def render_ui(self):
        st.set_page_config(page_title="AI秒算遺產稅", layout="wide")

        st.markdown("<h1 style='text-align:center; color:black;'>AI秒算遺產稅</h1>", unsafe_allow_html=True)

        # Step 1: 地區
        st.selectbox("選擇適用地區", ["台灣（2025年起）"], index=0)

        # Step 2: 總資產
        total_assets_input = st.number_input(
            "總資產（萬）", min_value=1000, max_value=100000,
            value=5000, step=100, help="請輸入您的總資產（單位：萬）"
        )

        # Step 3: 家庭成員
        st.markdown("### 請輸入家庭成員數")
        has_spouse = st.checkbox("是否有配偶（扣除額 553 萬）", value=False)
        adult_children_input = st.number_input("直系血親卑親屬數（每人 56 萬）", 0, 10, 0)
        parents_input = st.number_input("父母數（每人 138 萬，最多 2 人）", 0, 2, 0)
        max_disabled = (1 if has_spouse else 0) + adult_children_input + parents_input
        disabled_people_input = st.number_input("重度以上身心障礙者數（每人 693 萬）", 0, max_disabled, 0)
        other_dependents_input = st.number_input("受撫養之兄弟姊妹、祖父母數（每人 56 萬）", 0, 5, 0)

        # 計算
        try:
            taxable_amount, tax_due, total_deductions = self.calculator.calculate_estate_tax(
                total_assets_input, has_spouse, adult_children_input,
                other_dependents_input, disabled_people_input, parents_input
            )
        except Exception as e:
            st.error(f"計算遺產稅時發生錯誤：{e}")
            return

        st.markdown(f"## 預估遺產稅：{int(tax_due):,} 萬元")

        # 三欄呈現
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
            st.table(df_deductions.astype(int))
        with col3:
            st.markdown("**稅務計算**")
            st.table(pd.DataFrame({
                "項目": ["課稅淨額", "遺產稅"],
                "金額（萬）": [int(taxable_amount), int(tax_due)]
            }))

        # 🔹 顧問式策略建議
        st.markdown("---")
        st.markdown("## 家族傳承策略建議")
        st.markdown(
            """
            1. **規劃保單**：透過保險預留稅源，確保資產分配順利。  
            2. **提前贈與**：利用免稅額逐年移轉財富，減少稅負。  
            3. **分散配置**：合理安排資產結構，兼顧流動性與節稅效果。  
            """
        )

        # 模擬試算
        st.markdown("---")
        st.markdown("## 策略模擬（登入後可用）")

        login_container = st.empty()
        if not st.session_state.get("authenticated", False):
            with login_container.form("login_form"):
                st.markdown("請先登入以檢視模擬試算。")
                login_username = st.text_input("帳號")
                login_password = st.text_input("密碼", type="password")
                if st.form_submit_button("登入"):
                    valid, user_name = check_credentials(login_username, login_password)
                    if valid:
                        st.session_state.authenticated = True
                        st.success(f"登入成功！歡迎 {user_name}")
                        time.sleep(1)
                        login_container.empty()

        if st.session_state.get("authenticated", False):
            st.markdown("### 模擬參數設定")
            gift_case = st.number_input("提前贈與金額（萬）", 0, total_assets_input, 0, step=100)
            premium_case = st.number_input("購買保險保費（萬）", 0, total_assets_input, 0, step=100)
            claim_case = st.number_input("保險理賠金（萬）", 0, 100000, 0, step=100)

            # 策略計算
            _, tax_case_no_plan, _ = self.calculator.calculate_estate_tax(
                total_assets_input, has_spouse, adult_children_input,
                other_dependents_input, disabled_people_input, parents_input
            )
            net_case_no_plan = total_assets_input - tax_case_no_plan

            effective_case_gift = total_assets_input - gift_case
            _, tax_case_gift, _ = self.calculator.calculate_estate_tax(
                effective_case_gift, has_spouse, adult_children_input,
                other_dependents_input, disabled_people_input, parents_input
            )
            net_case_gift = effective_case_gift - tax_case_gift + gift_case

            effective_case_insurance = total_assets_input - premium_case
            _, tax_case_insurance, _ = self.calculator.calculate_estate_tax(
                effective_case_insurance, has_spouse, adult_children_input,
                other_dependents_input, disabled_people_input, parents_input
            )
            net_case_insurance = effective_case_insurance - tax_case_insurance + claim_case

            # ➕ 贈與＋保單
            effective_case_combo = total_assets_input - gift_case - premium_case
            _, tax_case_combo, _ = self.calculator.calculate_estate_tax(
                effective_case_combo, has_spouse, adult_children_input,
                other_dependents_input, disabled_people_input, parents_input
            )
            net_case_combo = effective_case_combo - tax_case_combo + gift_case + claim_case

            # ➕ 贈與＋保單（實質課稅）
            effective_case_combo_tax = total_assets_input - gift_case - premium_case + claim_case
            _, tax_case_combo_tax, _ = self.calculator.calculate_estate_tax(
                effective_case_combo_tax, has_spouse, adult_children_input,
                other_dependents_input, disabled_people_input, parents_input
            )
            net_case_combo_tax = effective_case_combo_tax - tax_case_combo_tax + gift_case

            # 表格
            df_case = pd.DataFrame({
                "策略": ["沒有規劃", "提前贈與", "購買保險", "提前贈與＋購買保險", "提前贈與＋購買保險（被實質課稅）"],
                "遺產稅（萬）": [int(tax_case_no_plan), int(tax_case_gift),
                            int(tax_case_insurance), int(tax_case_combo), int(tax_case_combo_tax)],
                "家人總共取得（萬）": [int(net_case_no_plan), int(net_case_gift),
                                int(net_case_insurance), int(net_case_combo), int(net_case_combo_tax)]
            })
            baseline = df_case.loc[df_case["策略"] == "沒有規劃", "家人總共取得（萬）"].iloc[0]
            df_case["規劃效益"] = df_case["家人總共取得（萬）"] - baseline
            st.table(df_case)

            # 圖表
            fig_bar = px.bar(
                df_case, x="策略", y="家人總共取得（萬）",
                text="家人總共取得（萬）",
                title="不同策略下家人總共取得金額比較"
            )
            fig_bar.update_traces(texttemplate="%{text:.0f}", textposition="outside", marker_color="#2a9d8f")
            fig_bar.update_layout(
                yaxis_range=[0, df_case["家人總共取得（萬）"].max() * 1.3],
                font=dict(size=18, color="black"),
                title_font=dict(size=22, color="black"),
                height=600
            )
            st.plotly_chart(fig_bar, config={"responsive": True})


if __name__ == "__main__":
    constants = TaxConstants()
    calculator = EstateTaxCalculator(constants)
    ui = EstateTaxUI(calculator)
    ui.render_ui()
