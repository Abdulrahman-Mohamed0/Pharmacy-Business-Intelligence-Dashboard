"""
==============================================================
 2) هندسة المتغيرات (Feature Engineering) + تعريف الهدف
==============================================================
الهدف التنبؤي (Target):
    "هل الدواء ده هيتعرض لنقص فعلي خلال الـ 14 يوم الجايين؟" (0/1)

مهم جداً (منع تسريب البيانات / Data Leakage):
    كل الـ Features بتتحسب من الماضي فقط (Rolling على بيانات سابقة).
    الهدف (target) بس هو اللي بيبص للمستقبل - وده طبيعي لأننا
    بنعرّف الهدف من بيانات تدريب تاريخية معروفة بالكامل.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

HORIZON_DAYS = 14  # نافذة التنبؤ: هل هيحصل نقص خلال 14 يوم قدام

input_path = os.path.join(DATA_DIR, "historical_inventory.csv")
if not os.path.exists(input_path):
    raise FileNotFoundError(
        f"الملف مش موجود: {input_path}\n"
        "لازم تشغّل 01_generate_data.py الأول عشان يولّد الملف ده."
    )

df = pd.read_csv(input_path, parse_dates=["date"])
df = df.sort_values(["drug_name", "date"]).reset_index(drop=True)

feature_rows = []

for drug, g in df.groupby("drug_name", sort=False):
    g = g.reset_index(drop=True)

    # --- متوسطات متحركة للطلب (تُحسب من الماضي فقط) ---
    g["avg_demand_7d"] = g["daily_demand"].rolling(7, min_periods=3).mean()
    g["avg_demand_14d"] = g["daily_demand"].rolling(14, min_periods=5).mean()
    g["avg_demand_30d"] = g["daily_demand"].rolling(30, min_periods=10).mean()
    g["std_demand_30d"] = g["daily_demand"].rolling(30, min_periods=10).std()

    # --- اتجاه الطلب: هل بيزيد ولا بينقص مؤخراً؟ ---
    g["demand_trend"] = (g["avg_demand_7d"] - g["avg_demand_30d"]) / g["avg_demand_30d"].replace(0, np.nan)

    # --- أهم متغير: كام يوم متبقي على نفاذ المخزون بمعدل الاستهلاك الحالي ---
    g["days_of_stock_remaining"] = g["stock_level"] / g["avg_demand_14d"].replace(0, np.nan)

    # --- نسبة المخزون الحالي لنقطة إعادة الطلب ---
    g["stock_to_reorder_ratio"] = g["stock_level"] / g["reorder_point"]

    # --- هل المخزون فعلاً أقل من احتياج فترة التوريد؟ ---
    g["stock_vs_leadtime_demand"] = g["stock_level"] - (g["avg_demand_14d"] * g["lead_time_days"])

    # --- تكرار تأخيرات الموردين مؤخراً (مؤشر أزمة توريد قائمة) ---
    g["supplier_delay_rate_30d"] = g["supplier_delay_flag"].rolling(30, min_periods=5).mean()
    g["is_currently_on_order"] = g["on_order_flag"]

    # --- معدل النقص التاريخي لنفس الدواء (كم مرة حصل نقص قبل كده - Cumulative, من الماضي فقط) ---
    g["past_shortage_count"] = g["shortage_today"].shift(1).fillna(0).expanding().sum()
    g["past_shortage_rate"] = g["past_shortage_count"] / (g.index + 1)

    # --- سياق زمني (موسمية) ---
    g["month"] = g["date"].dt.month
    g["day_of_week"] = g["date"].dt.dayofweek
    g["day_of_year"] = g["date"].dt.dayofyear

    # ==========================================================
    # الهدف (Target): هل هيحصل نقص فعلي (stock<=0) خلال HORIZON_DAYS القادمة؟
    # (بنستخدم بيانات المستقبل هنا بس لتعريف الـ label، مش كـ feature)
    # ==========================================================
    shortage_arr = g["shortage_today"].values
    target = np.zeros(len(g), dtype=int)
    for i in range(len(g)):
        window_end = min(i + 1 + HORIZON_DAYS, len(g))
        target[i] = 1 if shortage_arr[i + 1: window_end].max(initial=0) > 0 else 0
    g["target_shortage_next_14d"] = target

    # استبعاد آخر HORIZON_DAYS يوم لهذا الدواء (مفيش بيانات مستقبل كافية لحساب الهدف بشكل صحيح)
    g = g.iloc[:-HORIZON_DAYS]

    feature_rows.append(g)

full = pd.concat(feature_rows, ignore_index=True)

# استبعاد الصفوف الأولى اللي الـ rolling features فيها لسه مش مكتملة (NaN)
full = full.dropna(subset=["avg_demand_30d", "days_of_stock_remaining", "supplier_delay_rate_30d"])

full.to_csv(os.path.join(DATA_DIR, "features_dataset.csv"), index=False)

print("تم بناء ملف الـ Features بنجاح")
print("الشكل:", full.shape)
print("توزيع الهدف:")
print(full["target_shortage_next_14d"].value_counts(normalize=True))
