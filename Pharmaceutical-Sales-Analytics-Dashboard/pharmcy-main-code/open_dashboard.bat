@echo off
REM ==============================================================
REM  تشغيل لوحة التحكم كموقع محلي - دبل كليك بس وهيفتح المتصفح
REM ==============================================================
cd /d "%~dp0"

echo بيتأكد إن المكتبات المطلوبة متثبتة...
python -m pip install streamlit plotly --quiet

if not exist "data\drug_prices.csv" (
    echo بيولّد ملف الأسعار لأول مرة...
    python 08_generate_prices.py
)

echo بيفتح لوحة التحكم في المتصفح...
python -m streamlit run 07_dashboard.py
pause