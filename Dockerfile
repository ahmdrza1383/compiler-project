# استفاده از نسخه سبک پایتون
FROM python:3.11-slim

# تنظیم پوشه کاری
WORKDIR /app

# کپی فایل‌های پروژه به داخل کانتینر
COPY . .

# نصب وابستگی‌ها (در این پروژه چیزی نداریم، اما می‌تواند برای آینده باشد)
RUN pip install --no-cache-dir -r requirements.txt

# دستور پیش‌فرض برای اجرای برنامه
CMD ["python", "main.py"]