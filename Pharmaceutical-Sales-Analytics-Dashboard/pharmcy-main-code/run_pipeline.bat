@echo off
REM ==============================================================
REM  ملف تشغيل تلقائي لـ Windows Task Scheduler
REM ==============================================================
REM  استخدمه ده في Task Scheduler بدل ما تكتب مسار python.exe يدوي.
REM  خطوات الإعداد:
REM   1. افتح Task Scheduler
REM   2. Create Basic Task -> اختار التوقيت (يومي مثلاً الساعة 6 الصبح)
REM   3. Action: Start a Program
REM   4. Program/script: اختار الملف ده (run_pipeline.bat)
REM   5. Start in: مسار مجلد المشروع (نفس مكان الملفات دي)
REM ==============================================================

cd /d "%~dp0"
python run_pipeline.py
pause
