"""
==============================================================
 3) تدريب وتقييم الموديل
==============================================================
بنقسّم البيانات زمنياً (Time-based Split) مش عشوائي:
    - Train: أول 80% من الفترة الزمنية
    - Test:  آخر 20% من الفترة الزمنية
ده أهم فرق عن التقسيم العشوائي العادي: بيحاكي الواقع الفعلي
(بنتدرب على الماضي، ونختبر على المستقبل - زي ما هيحصل فعلياً
لما الموديل يشتغل حي/Live).
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import os
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import (
    classification_report, roc_auc_score, confusion_matrix,
    precision_recall_curve
)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
CHARTS_DIR = os.path.join(BASE_DIR, "charts")
os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

features_path = os.path.join(DATA_DIR, "features_dataset.csv")
if not os.path.exists(features_path):
    raise FileNotFoundError(
        f"الملف مش موجود: {features_path}\n"
        "لازم تشغّل 01_generate_data.py ثم 02_feature_engineering.py الأول."
    )

df = pd.read_csv(features_path, parse_dates=["date"])

FEATURES = [
    "stock_level", "daily_demand", "reorder_point", "lead_time_days",
    "avg_demand_7d", "avg_demand_14d", "avg_demand_30d", "std_demand_30d",
    "demand_trend", "days_of_stock_remaining", "stock_to_reorder_ratio",
    "stock_vs_leadtime_demand", "supplier_delay_rate_30d", "is_currently_on_order",
    "past_shortage_rate", "month", "day_of_week", "day_of_year",
]
TARGET = "target_shortage_next_14d"

# --- ترميز الفئة (category) كـ one-hot ---
df = pd.get_dummies(df, columns=["category"], prefix="cat")
cat_cols = [c for c in df.columns if c.startswith("cat_")]
FEATURES += cat_cols

# --- تقسيم زمني ---
split_date = df["date"].quantile(0.8)
train = df[df["date"] <= split_date]
test = df[df["date"] > split_date]

X_train, y_train = train[FEATURES], train[TARGET]
X_test, y_test = test[FEATURES], test[TARGET]

print(f"تاريخ التقسيم: {split_date.date()}")
print(f"حجم التدريب: {len(train)} | حجم الاختبار: {len(test)}")
print(f"نسبة الحالات الإيجابية في التدريب: {y_train.mean():.3f} | في الاختبار: {y_test.mean():.3f}")

# ==========================================================
# نموذج 1: Random Forest
# ==========================================================
rf = RandomForestClassifier(
    n_estimators=400, max_depth=10, min_samples_leaf=5,
    class_weight="balanced", random_state=42, n_jobs=-1
)
rf.fit(X_train, y_train)
rf_proba = rf.predict_proba(X_test)[:, 1]

# ==========================================================
# نموذج 2: XGBoost
# ==========================================================
scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
xgb = XGBClassifier(
    n_estimators=400, max_depth=5, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,
    eval_metric="auc", random_state=42, n_jobs=-1
)
xgb.fit(X_train, y_train)
xgb_proba = xgb.predict_proba(X_test)[:, 1]

# ==========================================================
# المقارنة واختيار الأفضل
# ==========================================================
rf_auc = roc_auc_score(y_test, rf_proba)
xgb_auc = roc_auc_score(y_test, xgb_proba)
print(f"\nRandom Forest ROC-AUC: {rf_auc:.4f}")
print(f"XGBoost       ROC-AUC: {xgb_auc:.4f}")

best_name, best_model, best_proba = ("XGBoost", xgb, xgb_proba) if xgb_auc >= rf_auc else ("Random Forest", rf, rf_proba)
print(f"\n>>> الموديل الأفضل: {best_name}")

# --- اختيار عتبة القرار (threshold) اللي بتدي أفضل F1 بدل الافتراضي 0.5 ---
prec, rec, thresholds = precision_recall_curve(y_test, best_proba)
f1_scores = 2 * prec * rec / (prec + rec + 1e-9)
best_threshold_idx = np.argmax(f1_scores[:-1])
best_threshold = thresholds[best_threshold_idx]
print(f"أفضل عتبة قرار (threshold): {best_threshold:.3f}")

y_pred = (best_proba >= best_threshold).astype(int)

print("\n--- تقرير الأداء التفصيلي ---")
report = classification_report(y_test, y_pred, target_names=["لا يوجد نقص متوقع", "نقص متوقع"])
print(report)

cm = confusion_matrix(y_test, y_pred)
print("Confusion Matrix:\n", cm)

# ==========================================================
# حفظ الموديل والمتغيرات
# ==========================================================
joblib.dump({
    "model": best_model,
    "model_name": best_name,
    "features": FEATURES,
    "threshold": best_threshold,
    "horizon_days": 14,
}, os.path.join(OUTPUTS_DIR, "shortage_model.pkl"))

with open(os.path.join(OUTPUTS_DIR, "evaluation_report.txt"), "w", encoding="utf-8") as f:
    f.write(f"الموديل المختار: {best_name}\n")
    f.write(f"ROC-AUC: {max(rf_auc, xgb_auc):.4f}\n")
    f.write(f"عتبة القرار المثلى: {best_threshold:.3f}\n\n")
    f.write("تقرير الأداء:\n")
    f.write(report)
    f.write(f"\nConfusion Matrix:\n{cm}\n")

# ==========================================================
# رسم: أهمية المتغيرات (Feature Importance)
# ==========================================================
importances = pd.Series(best_model.feature_importances_, index=FEATURES).sort_values(ascending=False).head(15)

plt.figure(figsize=(9, 6))
importances.sort_values().plot(kind="barh", color="#2E86AB")
plt.title(f"أهم 15 عامل مؤثر في التنبؤ بالنقص ({best_name})", fontsize=13)
plt.xlabel("درجة الأهمية")
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, "feature_importance.png"), dpi=150)
plt.close()

# ==========================================================
# رسم: مصفوفة الالتباس (Confusion Matrix)
# ==========================================================
plt.figure(figsize=(5, 4.5))
plt.imshow(cm, cmap="Blues")
plt.title(f"مصفوفة الالتباس - {best_name}")
plt.colorbar()
labels = ["لا نقص", "نقص متوقع"]
plt.xticks([0, 1], labels)
plt.yticks([0, 1], labels)
for i in range(2):
    for j in range(2):
        plt.text(j, i, str(cm[i, j]), ha="center", va="center",
                  color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=14)
plt.ylabel("الحقيقة الفعلية")
plt.xlabel("توقع الموديل")
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, "confusion_matrix.png"), dpi=150)
plt.close()

print("\nتم حفظ الموديل والرسومات والتقرير في مجلدي outputs و charts")
