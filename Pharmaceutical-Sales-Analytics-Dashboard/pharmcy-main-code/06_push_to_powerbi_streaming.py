"""
==============================================================
 6) بث النتائج لحظياً إلى Power BI (Streaming Dataset) - اختياري
==============================================================
الفرق عن ملف 05: ده بيبعت البيانات مباشرة لـ Power BI عن طريق
API خاص بيهم اسمه "Streaming Dataset / Push Dataset"، فالداشبورد
بيتحدث فورًا من غير Scheduled Refresh وبدون قاعدة بيانات وسيطة.

⚠️ الطريقة دي مناسبة لأرقام ملخصة (KPIs) بتتحدث بشكل متكرر - زي
"عدد الأدوية شديدة الخطورة الآن" - مش مناسبة لجدول كامل بمئات الصفوف.

خطوات الإعداد على موقع Power BI (مرة واحدة بس):
    1. ادخل على https://app.powerbi.com
    2. My Workspace -> Create -> Streaming dataset
    3. اختار "API" كمصدر
    4. عرّف الأعمدة دي بالظبط (Text/Number/DateTime):
         drug_name           (Text)
         risk_probability    (Number)
         days_remaining      (Number)
         high_risk_count     (Number)
         snapshot_time       (DateTime)
    5. بعد الحفظ، Power BI هيديك "Push URL" - انسخه وحطه في
       PUSH_URL تحت.
    6. تقدر تعمل Tile/Card في الداشبورد يتغذى من الـ Streaming
       dataset ده مباشرة عشان يتحدث لحظيًا.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import os
import json
import datetime
import pandas as pd
import requests

# ==========================================================
# CONFIG - غيّر القيمة دي بالـ Push URL اللي هتاخده من Power BI
# ==========================================================
PUSH_URL = os.environ.get(
    "POWERBI_PUSH_URL",
    "PASTE_YOUR_POWER_BI_STREAMING_PUSH_URL_HERE"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

# أعلى كام دواء تحب تبعتهم كصفوف تفصيلية (باقي الحقول بتتبعت كملخص)
TOP_N_DRUGS_TO_PUSH = 10


def main():
    if PUSH_URL.startswith("PASTE_"):
        print("❌ لازم تحط الـ Push URL بتاعك من Power BI الأول.")
        print("   راجع تعليمات الإعداد في أول الملف ده.")
        return

    report_path = os.path.join(OUTPUTS_DIR, "current_risk_report.csv")
    if not os.path.exists(report_path):
        raise FileNotFoundError(
            f"الملف مش موجود: {report_path}\n"
            "لازم تشغّل 04_predict_current_risk.py الأول."
        )

    df = pd.read_csv(report_path)
    now_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

    high_risk_count = int((df["متوقع نقص خلال 14 يوم؟"] == 1).sum())
    top_drugs = df.sort_values("احتمال النقص %", ascending=False).head(TOP_N_DRUGS_TO_PUSH)

    rows_to_push = []
    for _, row in top_drugs.iterrows():
        rows_to_push.append({
            "drug_name": row["اسم الدواء"],
            "risk_probability": float(row["احتمال النقص %"]),
            "days_remaining": float(row["أيام متبقية تقريباً"]),
            "high_risk_count": high_risk_count,
            "snapshot_time": now_iso,
        })

    try:
        response = requests.post(
            PUSH_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(rows_to_push),
            timeout=15,
        )
    except requests.exceptions.RequestException as e:
        print(f"❌ فشل الاتصال بـ Power BI: {e}")
        return

    if response.status_code in (200, 201):
        print(f"✅ تم بث {len(rows_to_push)} صف إلى Power BI بنجاح.")
    else:
        print(f"❌ فشل الإرسال - كود الحالة: {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    main()
