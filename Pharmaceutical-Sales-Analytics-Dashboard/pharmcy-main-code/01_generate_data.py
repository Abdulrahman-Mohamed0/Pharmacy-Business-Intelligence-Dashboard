"""
==============================================================
 1) توليد بيانات تاريخية واقعية (Synthetic Data)
==============================================================
الهدف: محاكاة سجل يومي حقيقي لمخزون ومبيعات صيدلية/مستشفى لمدة سنتين
شامل: طلب متغير + موسمية + اتجاهات + تأخيرات موردين + نواقص فعلية حصلت.

ملاحظة مهمة جداً:
عندما يتوفر ملف البيانات الحقيقي، هذا الملف بالكامل يتم استبداله بخطوة
واحدة فقط: قراءة ملف Excel/CSV الحقيقي وتحويله لنفس شكل الأعمدة
الموجودة هنا (راجع README.md قسم "الانتقال للبيانات الحقيقية").
"""

import sys
if sys.platform == "win32":
    # يجبر بايثون يستخدم UTF-8 دايماً بدل ترميز الويندوز العربي (cp1256)
    # اللي مش بيقدر يمثل بعض الرموز أو النصوص، فبيمنع الإيرور ده
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import os
import numpy as np
import pandas as pd

np.random.seed(42)

# ---------------------------------------------------------------
# تحديد مسار المشروع تلقائياً (بيشتغل على أي جهاز / أي نظام تشغيل)
# ---------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------------------
# إعداد قائمة أدوية بفئات مختلفة (كل فئة سلوك طلب مختلف)
# ---------------------------------------------------------------
DRUGS_RAW = [
    # (اسم الدواء, الفئة, متوسط طلب يومي, تقلب الطلب, مدة توريد بالأيام, احتمال أزمة توريد سنوياً)
    ("Paracetamol 500mg",      "Analgesic",        220, 0.35, 5,  0.03),
    ("Ibuprofen 400mg",        "Analgesic",         140, 0.30, 6,  0.03),
    ("Amoxicillin 500mg",      "Antibiotic",        95, 0.40, 10, 0.07),
    ("Azithromycin 250mg",     "Antibiotic",         55, 0.45, 12, 0.08),
    ("Ceftriaxone Inj 1g",     "Antibiotic",         30, 0.50, 15, 0.10),
    ("Metformin 500mg",        "Chronic-Diabetes",  180, 0.15, 14, 0.05),
    ("Insulin Glargine",       "Chronic-Diabetes",   40, 0.10, 20, 0.12),
    ("Atorvastatin 20mg",      "Chronic-Cardio",    120, 0.15, 12, 0.04),
    ("Amlodipine 5mg",         "Chronic-Cardio",    110, 0.15, 12, 0.04),
    ("Losartan 50mg",          "Chronic-Cardio",     90, 0.15, 12, 0.05),
    ("Salbutamol Inhaler",     "Respiratory",        60, 0.30, 14, 0.06),
    ("Prednisolone 5mg",       "Respiratory",         35, 0.30, 10, 0.05),
    ("Omeprazole 20mg",        "GI",                 150, 0.20, 8,  0.03),
    ("Ranitidine 150mg",       "GI",                  70, 0.25, 10, 0.04),
    ("ORS Sachets",            "GI",                 200, 0.45, 5,  0.02),
    ("Diazepam 5mg",           "CNS",                 25, 0.20, 15, 0.06),
    ("Sodium Valproate",       "CNS",                 20, 0.20, 18, 0.09),
    ("Heparin Inj",            "Anticoagulant",       18, 0.35, 20, 0.15),
    ("Warfarin 5mg",           "Anticoagulant",       22, 0.20, 15, 0.10),
    ("Iron Folic Acid",        "Supplement",         160, 0.30, 7,  0.02),
    ("Vitamin D3",             "Supplement",         130, 0.25, 7,  0.02),
    ("Hepatitis B Vaccine",    "Vaccine",             15, 0.20, 25, 0.14),
    ("Tetanus Vaccine",        "Vaccine",             18, 0.20, 25, 0.13),
    ("Normal Saline IV",       "IV-Fluid",           250, 0.30, 6,  0.05),
    ("Dextrose 5% IV",         "IV-Fluid",           140, 0.30, 6,  0.05),
    ("Adrenaline Inj",         "Emergency",           12, 0.30, 18, 0.11),
    ("Morphine Inj",           "Controlled",           8, 0.25, 22, 0.16),
    ("Tramadol 50mg",          "Controlled",           45, 0.30, 14, 0.09),
    ("Ceftazidime Inj",        "Antibiotic",           20, 0.45, 16, 0.12),
    ("Clopidogrel 75mg",       "Chronic-Cardio",       85, 0.15, 12, 0.05),
]

# نقطة إعادة الطلب المفروض تغطي فترة التوريد (Lead Time Demand) + هامش أمان
DRUGS = []
for name, category, base_demand, volatility, lead_time, disruption_prob in DRUGS_RAW:
    safety_factor = np.random.uniform(1.15, 1.45)
    reorder_point = int(round(base_demand * lead_time * safety_factor))
    DRUGS.append((name, category, base_demand, volatility, lead_time, reorder_point, disruption_prob * 2.2))

N_DAYS = 730  # سنتين
start_date = pd.Timestamp("2024-01-01")
dates = pd.date_range(start_date, periods=N_DAYS, freq="D")

records = []

for name, category, base_demand, volatility, lead_time, reorder_point, disruption_prob in DRUGS:

    stock = reorder_point * np.random.uniform(1.5, 2.5)  # مخزون بداية
    on_order = 0
    on_order_arrival = None
    in_disruption = False
    disruption_days_left = 0
    trend_slope = np.random.uniform(-0.03, 0.06)  # اتجاه بسيط صعود/هبوط للطلب مع الوقت

    for day_idx, d in enumerate(dates):
        # --- موسمية بسيطة (شتاء أعلى للتنفسي والمضادات، صيف أعلى للسوائل) ---
        month = d.month
        seasonal_factor = 1.0
        if category in ("Respiratory", "Antibiotic"):
            seasonal_factor = 1.35 if month in (11, 12, 1, 2) else 0.9
        elif category == "IV-Fluid":
            seasonal_factor = 1.25 if month in (6, 7, 8) else 0.95

        # --- اتجاه تدريجي فى الطلب ---
        trend_factor = 1 + trend_slope * (day_idx / 365)

        # --- ضجيج عشوائي حول الطلب ---
        demand = max(
            0,
            np.random.normal(base_demand * seasonal_factor * trend_factor, base_demand * volatility)
        )
        demand = int(round(demand))

        # --- بداية/استمرار أزمة توريد عشوائية (السبب الحقيقي وراء أغلب النواقص) ---
        if not in_disruption and np.random.random() < disruption_prob / 365:
            in_disruption = True
            disruption_days_left = np.random.randint(7, 30)

        supplier_delay_flag = 1 if in_disruption else 0

        if in_disruption:
            disruption_days_left -= 1
            if disruption_days_left <= 0:
                in_disruption = False

        # --- منطق إعادة الطلب (Reorder Logic) ---
        if stock <= reorder_point and on_order == 0:
            order_qty = reorder_point * np.random.uniform(1.3, 1.7)
            effective_lead_time = lead_time * (np.random.uniform(2.0, 4.0) if in_disruption else np.random.uniform(0.85, 1.15))
            on_order = order_qty
            on_order_arrival = day_idx + int(round(effective_lead_time))

        if on_order > 0 and on_order_arrival == day_idx:
            stock += on_order
            on_order = 0
            on_order_arrival = None

        # --- استهلاك المخزون ---
        stock = stock - demand
        shortage_today = 1 if stock <= 0 else 0
        stock = max(stock, 0)

        records.append({
            "date": d,
            "drug_name": name,
            "category": category,
            "stock_level": round(stock, 1),
            "daily_demand": demand,
            "reorder_point": reorder_point,
            "lead_time_days": lead_time,
            "supplier_delay_flag": supplier_delay_flag,
            "on_order_flag": 1 if on_order > 0 else 0,
            "shortage_today": shortage_today,
        })

df = pd.DataFrame.from_records(records)
df.to_csv(os.path.join(DATA_DIR, "historical_inventory.csv"), index=False)

print("تم توليد البيانات بنجاح")
print(df.shape)
print(df.head())
print("\nعدد أيام النقص الفعلية إجمالاً:", df["shortage_today"].sum())
print("نسبة أيام النقص من إجمالي الصفوف: %.2f%%" % (100 * df["shortage_today"].mean()))
