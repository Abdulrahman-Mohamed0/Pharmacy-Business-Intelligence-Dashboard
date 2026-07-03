"""
==============================================================
 0) تشغيل خط الأنابيب كامل (Pipeline Runner)
==============================================================
الملف ده بيشغّل الأربع ملفات بالترتيب الصح تلقائياً:
    01_generate_data.py -> 02_feature_engineering.py ->
    03_train_model.py   -> 04_predict_current_risk.py

الفايدة: بدل ما تشغّل كل ملف يدوي، تشغّل الملف ده بس (أو تخليه
يتشغّل تلقائياً كل يوم عن طريق Windows Task Scheduler).

ملحوظة: لو عندك بيانات حقيقية بقت متاحة (بدل التجريبية)، إنت
غالباً هتستبدل 01_generate_data.py بسكريبت بيقرأ ملفك الحقيقي،
والباقي (02, 03, 04) هيفضل شغال زي ما هو من غير أي تعديل.

طريقة الجدولة التلقائية (Windows Task Scheduler):
    1. افتح Task Scheduler من قائمة ابدأ.
    2. Create Basic Task -> اختار التوقيت (يومي/أسبوعي).
    3. Action: Start a Program.
    4. Program/script: مسار python.exe عندك (مثلاً:
       C:\\Users\\Mr\\AppData\\Local\\Programs\\Python\\Python312\\python.exe)
    5. Add arguments: run_pipeline.py
    6. Start in: مسار مجلد المشروع (اللي فيه الملفات دي كلها)
"""

import subprocess
import sys
import os
import datetime

if sys.platform == "win32":
    # يجبر بايثون يستخدم UTF-8 دايماً بدل ترميز الويندوز العربي (cp1256)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# ترتيب التشغيل الإجباري - كل خطوة بتحتاج مخرجات اللي قبلها
STEPS = [
    "01_generate_data.py",
    "02_feature_engineering.py",
    "03_train_model.py",
    "04_predict_current_risk.py",
]

# لو عايز تضيف تصدير لـ SQL Server أو Power BI بعد التنبؤ، فعّل السطرين دول
# (لازم تظبط الإعدادات جوه الملفين الأول - راجع تعليقات كل ملف)
OPTIONAL_STEPS = [
    # "05_export_to_sql.py",
    # "06_push_to_powerbi_streaming.py",
]


def run_step(script_name, log_file):
    script_path = os.path.join(BASE_DIR, script_name)
    if not os.path.exists(script_path):
        message = f"❌ الملف مش موجود: {script_name}"
        print(message)
        log_file.write(message + "\n")
        return False

    print(f"\n{'='*70}\n▶ بتشغيل: {script_name}\n{'='*70}")
    log_file.write(f"\n{'='*70}\n▶ بتشغيل: {script_name}\n{'='*70}\n")

    # PYTHONIOENCODING بتضمن إن أي ملف بايثون (حتى لو مش متعدّل) يكتب مخرجاته
    # بـ UTF-8 حتى لو بيتنفذ عن طريق pipe بدل الترمينال مباشرة
    child_env = os.environ.copy()
    child_env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=child_env,
    )

    print(result.stdout)
    log_file.write(result.stdout)

    if result.returncode != 0:
        print(f"❌ الملف {script_name} وقف بخطأ:\n{result.stderr}")
        log_file.write(f"❌ خطأ:\n{result.stderr}\n")
        return False

    return True


def main():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = os.path.join(LOG_DIR, f"run_{timestamp}.log")

    with open(log_path, "w", encoding="utf-8") as log_file:
        start_msg = f"بدء تشغيل خط الأنابيب: {datetime.datetime.now()}"
        print(start_msg)
        log_file.write(start_msg + "\n")

        all_steps = STEPS + OPTIONAL_STEPS
        for step in all_steps:
            success = run_step(step, log_file)
            if not success:
                fail_msg = f"\n🛑 توقف التشغيل عند: {step}\nراجع اللوج: {log_path}"
                print(fail_msg)
                log_file.write(fail_msg)
                sys.exit(1)

        done_msg = f"\n✅ اكتمل تشغيل خط الأنابيب بنجاح: {datetime.datetime.now()}"
        print(done_msg)
        log_file.write(done_msg + "\n")


if __name__ == "__main__":
    main()
