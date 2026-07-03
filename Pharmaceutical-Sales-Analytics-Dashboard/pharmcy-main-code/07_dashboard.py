"""
==============================================================
 7) لوحة تحكم ويب (Web Dashboard) - مخاطر النقص + المبيعات
==============================================================
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import os
import subprocess
import pandas as pd
import streamlit as st
import plotly.express as px

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

REPORT_PATH = os.path.join(OUTPUTS_DIR, "current_risk_report.csv")
INVENTORY_PATH = os.path.join(DATA_DIR, "historical_inventory.csv")
PRICES_PATH = os.path.join(DATA_DIR, "drug_prices.csv")

st.set_page_config(
    page_title="لوحة تحكم الصيدلية",
    page_icon="💊",
    layout="wide",
)


# ==========================================================
# تحميل البيانات
# ==========================================================
@st.cache_data
def load_report(path):
    return pd.read_csv(path, encoding="utf-8-sig")


def run_full_pipeline():
    pipeline_path = os.path.join(BASE_DIR, "run_pipeline.py")
    result = subprocess.run(
        [sys.executable, pipeline_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result


# ==========================================================
# HEADER
# ==========================================================
col_title, col_button = st.columns([4, 1])

with col_title:
    st.title("💊 لوحة تحكم الصيدلية")
    st.caption("مخاطر النقص + المبيعات والأرباح في مكان واحد")

with col_button:
    if st.button("🔄 تحديث البيانات الآن", use_container_width=True):
        with st.spinner("جارِ إعادة تشغيل البايبلاين..."):
            result = run_full_pipeline()

        if result.returncode == 0:
            st.success("تم التحديث بنجاح")
            st.cache_data.clear()
        else:
            st.error("حصل خطأ")
            st.code(result.stderr)

st.divider()

tab_risk, tab_sales = st.tabs(["📦 مخاطر النقص", "💰 المبيعات والأرباح"])


# ==========================================================
# TAB 1 - RISK
# ==========================================================
with tab_risk:
    if not os.path.exists(REPORT_PATH):
        st.warning("شغّل pipeline الأول")
    else:
        df = load_report(REPORT_PATH)

        COL_NAME = "اسم الدواء"
        COL_RISK = "احتمال النقص %"
        COL_PRED = "متوقع نقص خلال 14 يوم؟"

        high_risk_df = df[df[COL_PRED] == 1]

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("إجمالي الأدوية", len(df))
        k2.metric("أدوية خطر", len(high_risk_df))
        k3.metric("متوسط الخطر", f"{df[COL_RISK].mean():.1f}%")
        k4.metric(
            "أعلى خطر",
            df.sort_values(COL_RISK, ascending=False).iloc[0][COL_NAME]
        )

        st.divider()
        st.dataframe(df)


# ==========================================================
# TAB 2 - SALES
# ==========================================================
with tab_sales:
    if not os.path.exists(INVENTORY_PATH) or not os.path.exists(PRICES_PATH):
        st.warning("شغّل pipeline + generate prices")
    else:
        inv = pd.read_csv(INVENTORY_PATH, parse_dates=["date"])
        prices = pd.read_csv(PRICES_PATH, encoding="utf-8-sig")

        sales = inv.merge(prices, on="drug_name", how="left")

        sales["revenue"] = sales["daily_demand"] * sales["unit_price"]
        sales["cost"] = sales["daily_demand"] * sales["unit_cost"]
        sales["profit"] = sales["revenue"] - sales["cost"]

        # ======================================================
        # KPIs
        # ======================================================
        total_revenue = sales["revenue"].sum()
        total_cost = sales["cost"].sum()
        net_profit = sales["profit"].sum()
        profit_margin = (net_profit / total_revenue * 100) if total_revenue else 0

        def fmt_m(x):
            return f"{x/1e6:.2f} million"

        pharmacies_col = None
        for c in ["pharmacy", "pharmacy_id", "store_id"]:
            if c in sales.columns:
                pharmacies_col = c
                break

        total_pharmacies = sales[pharmacies_col].nunique() if pharmacies_col else 120
        revenue_per_pharmacy = total_revenue / total_pharmacies if total_pharmacies else 0

        low_profit_products = sales.groupby("drug_name")["profit"].sum()
        low_profit_products = (low_profit_products < low_profit_products.mean()).sum()

        # ======================================================
        # KPI CARDS (NEW LAYOUT)
        # ======================================================
        st.subheader("📊 KPIs Overview")

        k1, k2, k3, k4 = st.columns(4)

        k1.metric("Total Profit", fmt_m(total_revenue))
        k2.metric("Net Profit", fmt_m(net_profit), f"{profit_margin:.2f}%")
        k3.metric("Total Cost", fmt_m(total_cost))
        k4.metric("Low Profit Products", low_profit_products)

        k5, k6 = st.columns(2)

        k5.metric("Total Pharmacies", total_pharmacies)
        k6.metric("Revenue per Pharmacy", f"{revenue_per_pharmacy/1000:.2f} K")

        st.markdown("---")

        # ======================================================
        # CHARTS (UNCHANGED)
        # ======================================================
        by_drug = sales.groupby("drug_name")["revenue"].sum().sort_values(ascending=False).head(5)

        st.subheader("Top Drugs Revenue")
        st.bar_chart(by_drug)

        st.subheader("Full Data")
        st.dataframe(sales)