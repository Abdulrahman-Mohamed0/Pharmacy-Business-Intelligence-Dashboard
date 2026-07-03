"""
==============================================================
 5) تصدير تقرير المخاطر إلى SQL Server (اختياري)
==============================================================
الهدف: بدل ما Power BI يقرأ ملف current_risk_report.csv مباشرة،
نخزن النتيجة في جدول SQL Server، عشان:
    - Power BI يعمل Scheduled Refresh تلقائي من الجدول.
    - نحتفظ بتاريخ (snapshot) لكل تشغيل، فنقدر نعمل Trend Chart
      لعدد الأدوية المهددة عبر الوقت (مش بس آخر يوم).

قبل التشغيل، لازم:
    1. تثبت المكتبة: pip install pyodbc
    2. يكون عندك ODBC Driver for SQL Server متثبت على الجهاز
       (غالباً موجود مسبقاً لو عندك SQL Server Management Studio).
    3. تظبط الإعدادات في قسم CONFIG تحت (اسم السيرفر، اسم القاعدة).

طريقة الاتصال الافتراضية هنا هي Windows Authentication (Trusted
Connection) لأنها الأسهل للاستخدام المحلي. لو محتاج Username/Password
بدلها زي الشرح في التعليق جوه CONFIG.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import os
import pandas as pd
import datetime

# ==========================================================
# CONFIG - غيّر القيم دي حسب بيئتك
# ==========================================================
SQL_SERVER = os.environ.get("PHARMA_SQL_SERVER", "localhost")        # اسم أو IP السيرفر
SQL_DATABASE = os.environ.get("PHARMA_SQL_DATABASE", "PharmacyBI")   # اسم قاعدة البيانات (لازم تكون موجودة مسبقاً)
SQL_TABLE = "ShortageRiskReport"                                      # اسم الجدول اللي هيتعمل تلقائي

# لو عايز تستخدم Username/Password بدل Windows Authentication:
# SQL_USER = os.environ.get("PHARMA_SQL_USER", "")
# SQL_PASSWORD = os.environ.get("PHARMA_SQL_PASSWORD", "")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")


def get_connection():
    import pyodbc
    # Windows Authentication (الافتراضي - الأسهل للاستخدام المحلي)
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        f"Trusted_Connection=yes;"
    )
    # لو محتاج Username/Password، امسح السطرين فوق واستخدم ده بدلهم:
    # conn_str = (
    #     f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    #     f"SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
    #     f"UID={SQL_USER};PWD={SQL_PASSWORD};"
    # )
    return pyodbc.connect(conn_str)


def main():
    report_path = os.path.join(OUTPUTS_DIR, "current_risk_report.csv")
    if not os.path.exists(report_path):
        raise FileNotFoundError(
            f"الملف مش موجود: {report_path}\n"
            "لازم تشغّل 04_predict_current_risk.py الأول."
        )

    df = pd.read_csv(report_path)
    df["snapshot_date"] = datetime.date.today().isoformat()

    # ترتيب الأعمدة عشان تتوافق مع أسماء أعمدة SQL (من غير مسافات/عربي)
    df = df.rename(columns={
        "اسم الدواء": "drug_name",
        "المخزون الحالي": "stock_level",
        "أيام متبقية تقريباً": "days_of_stock_remaining",
        "متوسط الاستهلاك اليومي": "avg_daily_demand",
        "مدة التوريد (يوم)": "lead_time_days",
        "احتمال النقص %": "risk_probability_pct",
        "متوقع نقص خلال 14 يوم؟": "predicted_shortage",
    })

    try:
        conn = get_connection()
    except ImportError:
        print("❌ مكتبة pyodbc مش متثبتة. ثبتها بالأمر:\n    pip install pyodbc")
        return
    except Exception as e:
        print(f"❌ فشل الاتصال بـ SQL Server: {e}")
        print("تأكد إن SQL_SERVER و SQL_DATABASE في أول الملف صح، وإن السيرفر شغال.")
        return

    cursor = conn.cursor()

    # إنشاء الجدول لو مش موجود
    cursor.execute(f"""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{SQL_TABLE}' AND xtype='U')
        CREATE TABLE {SQL_TABLE} (
            drug_name NVARCHAR(200),
            stock_level FLOAT,
            days_of_stock_remaining FLOAT,
            avg_daily_demand FLOAT,
            lead_time_days INT,
            risk_probability_pct FLOAT,
            predicted_shortage INT,
            snapshot_date DATE
        )
    """)
    conn.commit()

    # إدراج الصفوف الجديدة (بنحتفظ بالتاريخ القديم عشان الـ Trend، مش بنمسحه)
    insert_sql = f"""
        INSERT INTO {SQL_TABLE}
        (drug_name, stock_level, days_of_stock_remaining, avg_daily_demand,
         lead_time_days, risk_probability_pct, predicted_shortage, snapshot_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    rows = df[[
        "drug_name", "stock_level", "days_of_stock_remaining", "avg_daily_demand",
        "lead_time_days", "risk_probability_pct", "predicted_shortage", "snapshot_date"
    ]].values.tolist()

    cursor.executemany(insert_sql, rows)
    conn.commit()
    conn.close()

    print(f"✅ تم تصدير {len(rows)} صف إلى الجدول [{SQL_TABLE}] في قاعدة [{SQL_DATABASE}]")
    print("دلوقتي تقدر تربط Power BI بالجدول ده وتعمل Scheduled Refresh.")


if __name__ == "__main__":
    main()
