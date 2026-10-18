## التثبيت و التشغيل بأمر واحد

### ويندوز (انسخه للصاقه)
```bat
git clone https://github.com/Avetaar/AvetaarEFoot.git && cd AvetaarEFoot && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && python AvetaarEFoot.py
```

### لينكس / ماك (انسخه للصاقه)
```bash
git clone https://github.com/Avetaar/AvetaarEFoot.git && cd AvetaarEFoot && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python AvetaarEFoot.py
```

### أو شغل سكربت التثبيت الجاهز
```
AvetaarEFoot_run.bat      (ويندوز — شغل وضع الترمينال)
AvetaarEFoot_run.bat bot  (ويندوز — شغل وضع البوت)
./AvetaarEFoot_run.sh     (لينكس/ماك — شغل وضع الترمينال)
./AvetaarEFoot_run.sh bot (لينكس/ماك — شغل وضع البوت)
```
# Avetaar EFootball Player
## eFootball 2022 (PES) دليل الاستعلام عن اللاعبين

مشروع واحد، وجهان:
- **طرفية** (ترمنال) — ألوان، قوائم، بطاقات لاعبين.
- **بوت تلغرام** — أزرار ملونة، استعلام مباشر من الدردشة.

بيانات اللاعبين من eFootball 2022 API المجاني.

## التثبيت (أمر واحد)

```bash
pip install -r requirements.txt
```

## شغل الطرفية

```bash
python AvetaarEFoot.py
```

## شغل البوت

1. أنشئ بوتاً مع [@BotFather](https://t.me/BotFather) واكتب التوكن في ملف `
   ```env
   BOT_TOKEN=1234567890:AAA...
   ```
2. شغّل:
   ```bash
   python AvetaarEFoot.py --bot
   ```

## الاستخدام في البوت

| الأمر / النَص | الوظيفة |
|---|---|
| `/start` | يفتح القوائم (أزرار الملعب) |
| `/help` | دليل سريع |
| `/player mbappe` | استعلام لاعب بمعين |
| أي اسم بالإنجليزية | يستعلم اللاعب مباشرةً |
| زر 🔍 في القائمة | استعلام لاعب معيّن |

## ملاحظات

- الأسماء تُقبل **بالإنجليزية بدون مسافات** (مثل `mbappe`، `messi`، `kane`، `neuer`).
- لا يحتاج المشروع أي مفاتيح API — eFootball API عام.
- ملف `
