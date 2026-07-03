"""
==============================================================
 4) تقرير المخاطر الحالي (Live Risk Report)
==============================================================
بياخد آخر يوم متاح لكل دواء، ويطلعلك قايمة مرتبة بالأدوية
الأعلى خطورة للتعرض لنقص خلال الـ 14 يوم الجايين.

ده السكريبت اللي هتشغله يومياً/أسبوعياً على بياناتك الحقيقية
بعد ما الموديل يتدرب مرة واحدة.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import os
import pandas as pd
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

model_path = os.path.join(OUTPUTS_DIR, "shortage_model.pkl")
if not os.path.exists(model_path):
    raise FileNotFoundError(
        f"الملف مش موجود: {model_path}\n"
        "لازم تشغّل 03_train_model.py الأول عشان الموديل يتدرب ويتحفظ."
    )

bundle = joblib.load(model_path)
model = bundle["model"]
FEATURES = bundle["features"]
threshold = bundle["threshold"]

features_path = os.path.join(DATA_DIR, "features_dataset.csv")
df = pd.read_csv(features_path, parse_dates=["date"])
df = pd.get_dummies(df, columns=["category"], prefix="cat")

# التأكد من وجود كل الأعمدة المطلوبة (لو دواء/فئة مش موجودة في آخر يوم)
for col in FEATURES:
    if col not in df.columns:
        df[col] = 0

latest_date = df["date"].max()
latest = df[df["date"] == latest_date].copy()

latest["risk_probability"] = model.predict_proba(latest[FEATURES])[:, 1]
latest["predicted_shortage"] = (latest["risk_probability"] >= threshold).astype(int)

report = latest[[
    "drug_name", "stock_level", "days_of_stock_remaining",
    "avg_demand_14d", "lead_time_days", "risk_probability", "predicted_shortage"
]].sort_values("risk_probability", ascending=False)

report["risk_probability"] = (report["risk_probability"] * 100).round(1)
report["days_of_stock_remaining"] = report["days_of_stock_remaining"].round(1)
report["avg_demand_14d"] = report["avg_demand_14d"].round(1)

report.columns = [
    "اسم الدواء", "المخزون الحالي", "أيام متبقية تقريباً",
    "متوسط الاستهلاك اليومي", "مدة التوريد (يوم)", "احتمال النقص %", "متوقع نقص خلال 14 يوم؟"
]

report.to_csv(os.path.join(OUTPUTS_DIR, "current_risk_report.csv"),
              index=False, encoding="utf-8-sig")

print(f"تقرير المخاطر بتاريخ: {latest_date.date()}\n")
print("="*90)
high_risk = report[report["متوقع نقص خلال 14 يوم؟"] == 1]
if len(high_risk) > 0:
    print(f"\n⚠️  أدوية متوقع نقصها خلال الـ 14 يوم القادمة ({len(high_risk)} دواء):\n")
    print(high_risk.drop(columns=["متوقع نقص خلال 14 يوم؟"]).to_string(index=False))
else:
    print("\n✅ لا توجد أدوية في منطقة الخطر العالي حالياً")

print("\n" + "="*90)
print("\nأعلى 10 أدوية من حيث نسبة الخطورة (كل الأدوية):\n")
print(report.drop(columns=["متوقع نقص خلال 14 يوم؟"]).head(10).to_string(index=False))

print(f"\n\nتم حفظ التقرير الكامل في: outputs/current_risk_report.csv")
