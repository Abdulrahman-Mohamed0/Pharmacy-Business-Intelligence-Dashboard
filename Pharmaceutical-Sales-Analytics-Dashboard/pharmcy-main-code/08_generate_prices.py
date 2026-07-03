"""
==============================================================
 8) توليد أسعار وتكاليف الأدوية (لحساب الإيراد والربح)
==============================================================
ملف بيانات المخزون الأساسي (historical_inventory.csv) فيه كمية
مباعة ومخزون بس - من غير سعر بيع أو تكلفة. عشان نقدر نحسب "الإيراد"
و"الربح" زي داشبورد Power BI، محتاجين سعر وتكلفة لكل دواء.

الملف ده بيولّد سعر بيع وتكلفة واقعية تقريبية لكل دواء حسب فئته
(مضادات حيوية أغلى من مسكنات، أدوية مزمنة سعرها متوسط... إلخ).

⚠️ الأسعار دي تقديرية بس للتجربة. لو عندك ملف أسعار حقيقي (Excel/CSV
فيه drug_name, unit_price, unit_cost)، استبدل الملف ده بقراءة ملفك
مباشرة - نفس الفكرة المتبعة مع بيانات المخزون.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import os
import numpy as np
import pandas as pd

np.random.seed(7)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# نفس أسماء وفئات الأدوية الموجودة في 01_generate_data.py بالظبط
DRUGS_RAW = [
    ("Paracetamol 500mg",      "Analgesic"),
    ("Ibuprofen 400mg",        "Analgesic"),
    ("Amoxicillin 500mg",      "Antibiotic"),
    ("Azithromycin 250mg",     "Antibiotic"),
    ("Ceftriaxone Inj 1g",     "Antibiotic"),
    ("Metformin 500mg",        "Chronic-Diabetes"),
    ("Insulin Glargine",       "Chronic-Diabetes"),
    ("Atorvastatin 20mg",      "Chronic-Cardio"),
    ("Amlodipine 5mg",         "Chronic-Cardio"),
    ("Losartan 50mg",          "Chronic-Cardio"),
    ("Salbutamol Inhaler",     "Respiratory"),
    ("Prednisolone 5mg",       "Respiratory"),
    ("Omeprazole 20mg",        "GI"),
    ("Ranitidine 150mg",       "GI"),
    ("ORS Sachets",            "GI"),
    ("Diazepam 5mg",           "CNS"),
    ("Sodium Valproate",       "CNS"),
    ("Heparin Inj",            "Anticoagulant"),
    ("Warfarin 5mg",           "Anticoagulant"),
    ("Iron Folic Acid",        "Supplement"),
    ("Vitamin D3",             "Supplement"),
    ("Hepatitis B Vaccine",    "Vaccine"),
    ("Tetanus Vaccine",        "Vaccine"),
    ("Normal Saline IV",       "IV-Fluid"),
    ("Dextrose 5% IV",         "IV-Fluid"),
    ("Adrenaline Inj",         "Emergency"),
    ("Morphine Inj",           "Controlled"),
    ("Tramadol 50mg",          "Controlled"),
    ("Ceftazidime Inj",        "Antibiotic"),
    ("Clopidogrel 75mg",       "Chronic-Cardio"),
]

# (حد أدنى للسعر, حد أقصى للسعر, نسبة التكلفة من السعر: أدنى, أقصى) بالجنيه المصري
CATEGORY_PRICING = {
    "Analgesic":         (5, 20, 0.55, 0.70),
    "Antibiotic":        (25, 90, 0.50, 0.65),
    "Chronic-Diabetes":  (30, 120, 0.55, 0.70),
    "Chronic-Cardio":    (20, 70, 0.55, 0.70),
    "Respiratory":       (35, 110, 0.50, 0.65),
    "GI":                (10, 40, 0.55, 0.70),
    "CNS":               (20, 65, 0.50, 0.65),
    "Anticoagulant":     (40, 130, 0.50, 0.65),
    "Supplement":        (8, 30, 0.60, 0.75),
    "Vaccine":           (90, 250, 0.45, 0.60),
    "IV-Fluid":          (15, 45, 0.60, 0.75),
    "Emergency":         (50, 150, 0.45, 0.60),
    "Controlled":        (35, 110, 0.45, 0.60),
}

records = []
for name, category in DRUGS_RAW:
    p_min, p_max, c_min, c_max = CATEGORY_PRICING[category]
    unit_price = round(np.random.uniform(p_min, p_max), 2)
    cost_ratio = np.random.uniform(c_min, c_max)
    unit_cost = round(unit_price * cost_ratio, 2)
    records.append({
        "drug_name": name,
        "category": category,
        "unit_price": unit_price,
        "unit_cost": unit_cost,
    })

df = pd.DataFrame(records)
df.to_csv(os.path.join(DATA_DIR, "drug_prices.csv"), index=False, encoding="utf-8-sig")

print("تم توليد ملف الأسعار بنجاح")
print(df.head(10))
