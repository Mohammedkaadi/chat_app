FishShop (نسخة أولية)

تشغيل محلي:
1. pip install -r requirements.txt
2. python app.py
3. افتح http://127.0.0.1:5000

ملاحظات للنشر:
- ضع SECRET_KEY و ADMIN_PASS كمتغيرات بيئة في Railway.
- لتمكين دفع فعلي، اربط بوابة دفع تدعم SAR.
- لتحويل التخزين إلى إنتاجي استخدم Postgres و S3 لرفع الصور.
