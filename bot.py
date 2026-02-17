import telebot
from github import Github
import os
import json
import base64
from io import BytesIO

# ------------------ الإعدادات ------------------
TOKEN = "8589018354:AAFn-l1kOlaByMZRiIPHyb7660GwRR1ITxc"
ADMIN_ID = 7989584978
GITHUB_TOKEN = "ghp_ضع_هنا_توكن_جيتهاب"  # أنشئ توكن من GitHub Settings -> Developer settings -> Personal access tokens
REPO_NAME = "اسم_المستخدم/اسم_المستودع"  # مثلاً "ahmed/nour-alhuda"

# مسارات الملفات في المستودع
DATA_JSON_PATH = "data.json"
FILES_BASE = "files/"

# ------------------ تهيئة البوت و GitHub ------------------
bot = telebot.TeleBot(TOKEN)
g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

# قاموس لتخزين حالة المستخدمين (الملف/النص المؤقت)
user_data = {}

# ------------------ دوال مساعدة للتعامل مع GitHub ------------------
def get_file_content(path):
    """قراءة محتوى ملف من GitHub وإرجاع (المحتوى, sha)"""
    try:
        contents = repo.get_contents(path)
        content = base64.b64decode(contents.content).decode('utf-8')
        return content, contents.sha
    except:
        return None, None

def update_file(path, content, message, sha=None):
    """تحديث أو إنشاء ملف على GitHub"""
    if sha:
        repo.update_file(path, message, content, sha)
    else:
        repo.create_file(path, message, content)

def upload_file_to_github(file_bytes, file_name, folder):
    """رفع ملف ثنائي (PDF أو صورة) إلى مجلد معين"""
    path = f"{FILES_BASE}{folder}/{file_name}"
    try:
        # التحقق إذا كان الملف موجوداً
        contents = repo.get_contents(path)
        sha = contents.sha
        repo.update_file(path, f"رفع {file_name}", file_bytes, sha)
    except:
        repo.create_file(path, f"رفع {file_name}", file_bytes)
    return path

def load_data():
    """تحميل data.json من GitHub"""
    content, _ = get_file_content(DATA_JSON_PATH)
    if content:
        return json.loads(content)
    return {"quran": [], "duas": [], "azkar": [], "images": []}

def save_data(data):
    """حفظ data.json إلى GitHub"""
    _, sha = get_file_content(DATA_JSON_PATH)
    update_file(DATA_JSON_PATH, json.dumps(data, ensure_ascii=False, indent=4), "تحديث data.json", sha)

# ------------------ أوامر البوت ------------------
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "مرحباً بك في بوت إدارة نور الهدى.\nأرسل لي ملف PDF أو صورة أو نصاً، ثم اختر القسم المناسب.")

@bot.message_handler(commands=['admin_stats'])
def admin_stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    data = load_data()
    stats = f"الإحصائيات:\n"
    stats += f"القرآن: {len(data['quran'])} ملف\n"
    stats += f"الأدعية: {len(data['duas'])} نص\n"
    stats += f"الأذكار: {len(data['azkar'])} نص\n"
    stats += f"الصور: {len(data['images'])} صورة\n"
    bot.reply_to(message, stats)

# استقبال الملفات (PDF أو صور)
@bot.message_handler(content_types=['document', 'photo'])
def handle_file(message):
    if message.from_user.id != ADMIN_ID:
        return
    user_id = message.from_user.id
    if message.content_type == 'document':
        # ملف PDF
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
        if not file_name.lower().endswith('.pdf'):
            bot.reply_to(message, "الرجاء إرسال ملف PDF فقط.")
            return
        file_bytes = bot.download_file(file_info.file_path)
        user_data[user_id] = {'type': 'pdf', 'name': file_name, 'bytes': file_bytes}
    elif message.content_type == 'photo':
        # صورة (سنأخذ أعلى جودة)
        file_info = bot.get_file(message.photo[-1].file_id)
        file_name = f"image_{message.photo[-1].file_id}.jpg"
        file_bytes = bot.download_file(file_info.file_path)
        user_data[user_id] = {'type': 'image', 'name': file_name, 'bytes': file_bytes}
    
    # عرض أزرار الأقسام
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btn_quran = telebot.types.InlineKeyboardButton("القرآن الكريم", callback_data="section_quran")
    btn_duas = telebot.types.InlineKeyboardButton("الأدعية", callback_data="section_duas")
    btn_azkar = telebot.types.InlineKeyboardButton("الأذكار", callback_data="section_azkar")
    btn_gallery = telebot.types.InlineKeyboardButton("المعرض", callback_data="section_images")
    markup.add(btn_quran, btn_duas, btn_azkar, btn_gallery)
    bot.send_message(user_id, "اختر القسم الذي تريد إضافة الملف إليه:", reply_markup=markup)

# استقبال النصوص
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if message.from_user.id != ADMIN_ID:
        return
    user_id = message.from_user.id
    text = message.text
    if text.startswith('/'):  # نتجاهل الأوامر
        return
    user_data[user_id] = {'type': 'text', 'content': text, 'name': f"نص {len(text[:20])}..."}
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btn_quran = telebot.types.InlineKeyboardButton("القرآن الكريم", callback_data="section_quran")
    btn_duas = telebot.types.InlineKeyboardButton("الأدعية", callback_data="section_duas")
    btn_azkar = telebot.types.InlineKeyboardButton("الأذكار", callback_data="section_azkar")
    btn_gallery = telebot.types.InlineKeyboardButton("المعرض", callback_data="section_images")
    markup.add(btn_quran, btn_duas, btn_azkar, btn_gallery)
    bot.send_message(user_id, "اختر القسم الذي تريد إضافة النص إليه:", reply_markup=markup)

# معالجة الضغط على الأزرار
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    if user_id != ADMIN_ID:
        return
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "لا توجد بيانات مؤقتة. أرسل ملفاً أو نصاً أولاً.")
        return
    
    data = user_data[user_id]
    section = call.data.replace("section_", "")  # quran, duas, azkar, images
    folder_map = {'quran': 'quran', 'duas': 'duas', 'azkar': 'azkar', 'images': 'images'}
    folder = folder_map[section]
    
    try:
        # تحميل data.json الحالي
        json_data = load_data()
        
        if data['type'] == 'pdf' and section == 'quran':
            # رفع ملف PDF إلى GitHub
            file_path = upload_file_to_github(data['bytes'], data['name'], folder)
            # إضافة إلى data.json
            json_data['quran'].append({
                "name": data['name'],
                "url": f"https://raw.githubusercontent.com/{REPO_NAME}/main/{file_path}"
            })
            save_data(json_data)
            bot.send_message(user_id, f"✅ تم رفع ملف PDF بنجاح إلى قسم القرآن.")
        
        elif data['type'] == 'image' and section == 'images':
            file_path = upload_file_to_github(data['bytes'], data['name'], folder)
            json_data['images'].append({
                "name": data['name'],
                "url": f"https://raw.githubusercontent.com/{REPO_NAME}/main/{file_path}"
            })
            save_data(json_data)
            bot.send_message(user_id, f"✅ تم رفع الصورة بنجاح إلى المعرض.")
        
        elif data['type'] == 'text' and (section == 'duas' or section == 'azkar'):
            # إضافة النص إلى القسم المناسب
            new_item = {
                "name": data['name'],
                "content": data['content']
            }
            json_data[section].append(new_item)
            save_data(json_data)
            bot.send_message(user_id, f"✅ تم إضافة النص إلى قسم { 'الأدعية' if section=='duas' else 'الأذكار' }.")
        
        else:
            bot.send_message(user_id, "❌ نوع الملف لا يتوافق مع القسم المختار.")
        
        # حذف البيانات المؤقتة
        del user_data[user_id]
        bot.answer_callback_query(call.id, "تمت الإضافة بنجاح!")
        
    except Exception as e:
        bot.send_message(user_id, f"حدث خطأ: {str(e)}")
        bot.answer_callback_query(call.id, "فشل الإضافة")

# بدء تشغيل البوت
print("البوت يعمل...")
bot.infinity_polling()
