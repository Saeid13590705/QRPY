# QRPY
---
title: QRPY
emoji: 🎓
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: 1.30.0
app_file: app.py
pinned: false
license: mit
---

# 🎓 QRPY — آموزش گام‌به‌گام ساخت QR Code

پروژه‌ی آموزشی برای ساخت **QR Code Version 1** با **Error Correction Level L**
به‌صورت **گام‌به‌گام** و **قابل فهم برای دانش‌آموزان**.

## ✨ ویژگی‌ها

- نمایش گام‌به‌گام ۱۰ مرحله‌ی ساخت QR
- نمایش تمام محاسبات میانی (بیت‌ها، بایت‌ها، ماتریس‌ها)
- پیاده‌سازی کامل **Reed-Solomon** روی **GF(256)**
- نمایش **Zig-Zag placement** برای ۲۰۸ خانه‌ی داده
- نمایش **Mask Pattern 0** و **Format Information**
- رابط وب فارسی و راست‌به‌چپ

## 🚀 دموی آنلاین

- 🤗 [Hugging Face Spaces](https://huggingface.co/spaces/YOUR_USERNAME/QRPY)

## 📦 نصب و اجرا

```bash
pip install -r requirements.txt
streamlit run app.py
