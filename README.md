FishShop - متجر لبيع السمك الطازج (نسخة أولية)

تشغيل محلي:

1. أنشئ بيئة افتراضية (اختياري): python -m venv venv
2. تفعيل البيئة: (Windows) venv\Scripts\activate أو (Linux/Mac) source venv/bin/activate
3. تثبيت المتطلبات: pip install -r requirements.txt
4. تشغيل التطبيق: python app.py
5. افتح المتصفح: http://127.0.0.1:5000

للنشر على Railway:
- ارفع المستودع إلى GitHub.
- اربط المشروع بـ Railway وادخل متغيرات البيئة: SECRET_KEY و ADMIN_PASS.
- Railway سيستخدم Procfile لتشغيل التطبيق.

ملاحظات:
- الصور تحفظ محلياً في static/uploads. على بيئة إنتاج استخدم S3 أو خدمة تخزين سحابي لأن Railway قد يكون ephemeral.
- الدفع الحالي: دفع عند الاستلام (Cash on Delivery). لربط بوابة دفع فعليّة، أحتاج تفاصيل بوابة الدفع.
