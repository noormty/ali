import os
import telebot
import requests
import threading
import time
import zipfile
import tempfile
import random
import string
import shutil
from datetime import datetime, timedelta
import pytz
from github import Github

# استيراد توكن البوت من المتغيرات البيئية
bot_token = "7957140088:AAFpE8ujnsQQYedKBSe4c0-H7GAeHxVD-Ro"
github_token = "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"

# إنشاء كائن البوت
bot = telebot.TeleBot(bot_token)

# الهيروكو API
HEROKU_BASE_URL = 'https://api.heroku.com'

g = Github(github_token)
# قائمة التطبيقات المجدولة للحذف الذاتي
self_deleting_apps = {}

# تخزين حسابات المستخدم
user_accounts = {}

# قائمة لتخزين الأحداث
events = []

# دالة لإنشاء الأزرار وتخصيصها
def create_main_buttons():
    markup = telebot.types.InlineKeyboardMarkup()
    button1 = telebot.types.InlineKeyboardButton("إضافة حساب ➕", callback_data="add_account")
    button2 = telebot.types.InlineKeyboardButton("حساباتك 🗂️", callback_data="list_accounts")
    button3 = telebot.types.InlineKeyboardButton("قسم جيتهاب 🛠️", callback_data="github_section")
    button4 = telebot.types.InlineKeyboardButton("الأحداث 🔄", callback_data="show_events")
    markup.add(button1, button2)
    markup.add(button3)
    markup.add(button4)
    return markup

def create_github_control_buttons():
    markup = telebot.types.InlineKeyboardMarkup()
    delete_all_button = telebot.types.InlineKeyboardButton("حذف الكل 🗑️", callback_data="delete_all_repos")
    delete_repo_button = telebot.types.InlineKeyboardButton("حذف مستودع 🗑️", callback_data="delete_repo")
    upload_file_button = telebot.types.InlineKeyboardButton("رفع ملف 📤", callback_data="upload_file")
    list_repos_button = telebot.types.InlineKeyboardButton("عرض مستودعات GitHub 📂", callback_data="list_github_repos")
    markup.row(delete_all_button, delete_repo_button)
    markup.row(upload_file_button)
    markup.add(list_repos_button)
    markup.add(telebot.types.InlineKeyboardButton("العودة ↩️", callback_data="go_back"))
    return markup

# دالة لإنشاء زر العودة
def create_back_button():
    markup = telebot.types.InlineKeyboardMarkup()
    back_button = telebot.types.InlineKeyboardButton("العودة ↩️", callback_data="go_back")
    markup.add(back_button)
    return markup

# دالة لإنشاء أزرار التحكم بالحسابات
def create_account_control_buttons(account_index):
    markup = telebot.types.InlineKeyboardMarkup()
    button1 = telebot.types.InlineKeyboardButton("جلب تطبيقات هيروكو 📦", callback_data=f"list_heroku_apps_{account_index}")
    button2 = telebot.types.InlineKeyboardButton("حذف تطبيق ❌", callback_data=f"delete_app_{account_index}")
    button3 = telebot.types.InlineKeyboardButton("الحذف الذاتي ⏲️", callback_data=f"self_delete_app_{account_index}")
    button4 = telebot.types.InlineKeyboardButton("الوقت المتبقي ⏳", callback_data="remaining_time")
    markup.add(button1) 
    markup.add(button2)
    markup.add(button3)
    markup.add(button4)
    markup.add(telebot.types.InlineKeyboardButton("العودة ↩️", callback_data="list_accounts"))
    return markup

# دالة لمعالجة الطلبات الواردة
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id not in user_accounts:
        user_accounts[user_id] = []
        events.append(f"انضم مستخدم جديد: [{message.from_user.first_name}](tg://user?id={user_id})")
    bot.send_message(message.chat.id, "مرحبًا بك! اضغط على الأزرار أدناه لتنفيذ الإجراءات.", reply_markup=create_main_buttons())

# دالة لإضافة حساب جديد
def add_account(call):
    msg = bot.edit_message_text("يرجى إرسال مفتاح API الخاص بحساب Heroku:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=create_back_button())
    bot.register_next_step_handler(msg, handle_new_account)

def handle_new_account(message):
    api_key = message.text.strip()
    user_id = message.from_user.id
    if api_key in [account['api_key'] for account in user_accounts[user_id]]:
        bot.send_message(message.chat.id, "هذا الحساب مضاف مسبقًا.", reply_markup=create_main_buttons())
    elif validate_heroku_api_key(api_key):
        user_accounts[user_id].append({'api_key': api_key})
        events.append(f"أضاف [{message.from_user.first_name}](tg://user?id={user_id}) حساب جديد: `{api_key[:-4]}****`")
        bot.send_message(message.chat.id, "تمت إضافة حساب Heroku بنجاح!", reply_markup=create_main_buttons())
    else:
        bot.send_message(message.chat.id, "مفتاح API غير صحيح. يرجى المحاولة مرة أخرى.", reply_markup=create_main_buttons())

# التحقق من صحة مفتاح API
def validate_heroku_api_key(api_key):
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/vnd.heroku+json; version=3'
    }
    response = requests.get(f'{HEROKU_BASE_URL}/apps', headers=headers)
    return response.status_code == 200

# عرض حسابات المستخدم
def list_accounts(call):
    user_id = call.from_user.id
    if user_id in user_accounts and user_accounts[user_id]:
        accounts_list = "\n".join([f"حساب {index + 1}: `{get_heroku_account_name(account['api_key'])}`" for index, account in enumerate(user_accounts[user_id])])
        markup = telebot.types.InlineKeyboardMarkup()
        for index in range(len(user_accounts[user_id])):
            account_name = get_heroku_account_name(user_accounts[user_id][index]['api_key'])
            markup.add(telebot.types.InlineKeyboardButton(f"{account_name}", callback_data=f"select_account_{index}"))
        markup.add(telebot.types.InlineKeyboardButton("العودة ↩️", callback_data="go_back"))
        bot.edit_message_text(f"حساباتك:\n{accounts_list}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    else:
        bot.edit_message_text("لا توجد حسابات مضافة.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=create_back_button())

# جلب اسم حساب هيروكو
def get_heroku_account_name(api_key):
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/vnd.heroku+json; version=3'
    }
    response = requests.get(f'{HEROKU_BASE_URL}/account', headers=headers)
    if response.status_code == 200:
        return response.json().get('email', 'Unknown')
    return 'Unknown'

# دالة لجلب تطبيقات هيروكو
def list_heroku_apps(call):
    account_index = int(call.data.split("_")[-1])
    user_id = call.from_user.id
    if not user_accounts[user_id]:
        bot.edit_message_text("لا توجد حسابات مضافة. يرجى إضافة حساب أولاً.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=create_back_button())
        return

    headers = {
        'Authorization': f'Bearer {user_accounts[user_id][account_index]["api_key"]}',
        'Accept': 'application/vnd.heroku+json; version=3'
    }
    bot.edit_message_text("جلب التطبيقات... ⬛⬜ 0%", chat_id=call.message.chat.id, message_id=call.message.message_id)
    time.sleep(2)
    response = requests.get(f'{HEROKU_BASE_URL}/apps', headers=headers)
    if response.status_code == 200:
        apps = response.json()
        apps_list = "\n".join([f"`{app['name']}`" for app in apps])
        bot.edit_message_text("جلب التطبيقات... ⬛⬛ 50%", chat_id=call.message.chat.id, message_id=call.message.message_id)
        time.sleep(2)
        bot.edit_message_text(f"التطبيقات المتاحة في هيروكو:\n{apps_list}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=create_back_button(), parse_mode='Markdown')
    else:
        bot.edit_message_text("حدث خطأ في جلب التطبيقات من هيروكو.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=create_back_button())

# دالة لمعالجة النقرات على الأزرار
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "add_account":
        add_account(call)
    elif call.data == "list_accounts":
        list_accounts(call)
    elif call.data == "show_events":
        show_events(call)
    elif call.data.startswith("select_account_"):
        account_index = int(call.data.split("_")[-1])
        bot.edit_message_text(f"إدارة حساب {account_index + 1}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=create_account_control_buttons(account_index))
    elif call.data.startswith("list_heroku_apps_"):
        list_heroku_apps(call)
    elif call.data.startswith("delete_app_"):
        account_index = int(call.data.split("_")[-1])
        msg = bot.edit_message_text("يرجى إرسال اسم التطبيق لحذفه:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=create_back_button())
        bot.register_next_step_handler(msg, lambda m: handle_app_name_for_deletion(m, account_index))
    elif call.data.startswith("self_delete_app_"):
        account_index = int(call.data.split("_")[-1])
        msg = bot.edit_message_text("يرجى إرسال اسم التطبيق للحذف الذاتي:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=create_back_button())
        bot.register_next_step_handler(msg, lambda m: handle_app_name_for_self_deletion(m, account_index))
    elif call.data == "remaining_time":
        show_remaining_time(call)
    elif call.data == "go_back":
        bot.edit_message_text("مرحبًا بك! اضغط على الأزرار أدناه لتنفيذ الإجراءات.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=create_main_buttons())
    elif call.data == "github_section":
        bot.edit_message_text("قسم جيتهاب:\nيرجى اختيار إحدى الخيارات:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=create_github_control_buttons())
    elif call.data == "upload_file":
        msg = bot.send_message(call.message.chat.id, "يرجى إرسال ملف مضغوط بصيغة ZIP.")
        bot.register_next_step_handler(msg, handle_zip_file)
    elif call.data == "list_github_repos":
        list_github_repos(call)
    elif call.data == "delete_repo":
        msg = bot.send_message(call.message.chat.id, "يرجى إرسال اسم المستودع لحذفه.")
        bot.register_next_step_handler(msg, handle_repo_deletion)
    elif call.data == "delete_all_repos":
        delete_all_repos(call)

# دالة لحذف مستودع
def handle_repo_deletion(message):
    repo_name = message.text.strip()
    user = g.get_user()
    try:
        repo = user.get_repo(repo_name)
        repo.delete()
        bot.send_message(message.chat.id, f"تم حذف المستودع `{repo_name}` بنجاح.", parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, f"المستودع `{repo_name}` غير موجود أو لا تملك صلاحية حذفه.", parse_mode='Markdown')

# دالة لحذف جميع المستودعات
def delete_all_repos(call):
    user = g.get_user()
    repos = user.get_repos()
    repo_count = repos.totalCount
    for repo in repos:
        repo.delete()
    bot.edit_message_text(f"تم حذف جميع المستودعات بنجاح.\nعدد المستودعات المحذوفة: {repo_count}", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='Markdown', reply_markup=create_back_button())

# دالة لعرض مستودعات GitHub
def list_github_repos(call):
    user = g.get_user()
    repos = user.get_repos()
    repo_list = ""
    loading_message = bot.send_message(call.message.chat.id, "جارٍ جلب المستودعات، يرجى الانتظار...")

    for repo in repos:
        try:
            contents = repo.get_contents("")
            num_files = sum(1 for _ in contents)
            repo_list += f"📂 *اسم المستودع*: `{repo.name}`\n📁 *عدد الملفات*: {num_files}\n\n"
        except:
            pass

    if repo_list:
        bot.edit_message_text(f"مستودعات GitHub:\n{repo_list}", chat_id=call.message.chat.id, message_id=loading_message.message_id, parse_mode='Markdown', reply_markup=create_back_button())
    else:
        bot.edit_message_text("لا توجد مستودعات لعرضها.", chat_id=call.message.chat.id, message_id=loading_message.message_id, parse_mode='Markdown', reply_markup=create_back_button())

# دالة لمعالجة الملف المضغوط
# دالة لمعالجة ملف ZIP
def handle_zip_file(message):
    if message.document and message.document.mime_type == 'application/zip':
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, message.document.file_name)
            with open(zip_path, 'wb') as new_file:
                new_file.write(downloaded_file)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                repo_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                user = g.get_user()
                repo = user.create_repo(repo_name, private=True)
                
                for root, dirs, files in os.walk(temp_dir):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        relative_path = os.path.relpath(file_path, temp_dir)
                        with open(file_path, 'rb') as file_data:
                            repo.create_file(relative_path, f"Add {relative_path}", file_data.read())
                
                num_files = sum([len(files) for r, d, files in os.walk(temp_dir)])
                bot.send_message(message.chat.id, f"تم إنشاء المستودع بنجاح.\nاسم المستودع: `{repo_name}`\nعدد الملفات: {num_files}", parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "الملف الذي تم إرساله ليس ملف ZIP. يرجى المحاولة مرة أخرى.")

# دالة لعرض الأحداث
def show_events(call):
    if not events:
        bot.edit_message_text("لا توجد أحداث لعرضها.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=create_back_button())
    else:
        events_list = "\n".join(events)
        bot.edit_message_text(f"الأحداث:\n{events_list}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=create_back_button(), parse_mode='Markdown')

# دالة لمعالجة اسم التطبيق للحذف
def handle_app_name_for_deletion(message, account_index):
    app_name = message.text.strip()
    user_id = message.from_user.id
    headers = {
        'Authorization': f'Bearer {user_accounts[user_id][account_index]["api_key"]}',
        'Accept': 'application/vnd.heroku+json; version=3'
    }
    response = requests.delete(f'{HEROKU_BASE_URL}/apps/{app_name}', headers=headers)
    if response.status_code == 202:
        events.append(f"حذف [{message.from_user.first_name}](tg://user?id={user_id}) التطبيق: `{app_name[:-2]}**`")
        bot.send_message(message.chat.id, f"تم حذف التطبيق `{app_name}` بنجاح.", reply_markup=create_main_buttons(), parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, f"حدث خطأ أثناء محاولة حذف التطبيق `{app_name}`. يرجى المحاولة مرة أخرى.", reply_markup=create_main_buttons(), parse_mode='Markdown')

# دالة لمعالجة اسم التطبيق للحذف الذاتي
def handle_app_name_for_self_deletion(message, account_index):
    app_name = message.text.strip()
    user_id = message.from_user.id
    if app_name in self_deleting_apps:
        bot.send_message(message.chat.id, "تم جدولة الحذف الذاتي لهذا التطبيق مسبقًا.", reply_markup=create_main_buttons())
    else:
        delay = 24 * 60 * 60  # 24 ساعة
        self_deleting_apps[app_name] = threading.Timer(delay, delete_heroku_app, [app_name, user_accounts[user_id][account_index]["api_key"]])
        self_deleting_apps[app_name].start()
        events.append(f"قام [{message.from_user.first_name}](tg://user?id={user_id}) بتفعيل الحذف الذاتي للتطبيق: `{app_name[:-2]}**`")
        bot.send_message(message.chat.id, f"تم جدولة الحذف الذاتي للتطبيق `{app_name}` بعد 24 ساعة.", reply_markup=create_main_buttons(), parse_mode='Markdown')

# دالة لحذف تطبيق هيروكو بعد فترة
def delete_heroku_app(app_name, api_key):
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/vnd.heroku+json; version=3'
    }
    requests.delete(f'{HEROKU_BASE_URL}/apps/{app_name}', headers=headers)
    del self_deleting_apps[app_name]

# دالة لعرض الوقت المتبقي للحذف الذاتي
def show_remaining_time(call):
    user_id = call.from_user.id
    if not self_deleting_apps:
        bot.edit_message_text("لا توجد تطبيقات مجدولة للحذف الذاتي.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=create_back_button())
    else:
        remaining_times = []
        for app_name, timer in self_deleting_apps.items():
            remaining_time = timer.interval - (time.time() - timer.when)
            remaining_times.append(f"التطبيق: `{app_name[:-2]}**` - الوقت المتبقي: {str(timedelta(seconds=remaining_time))}")
        bot.edit_message_text("الوقت المتبقي للحذف الذاتي:\n" + "\n".join(remaining_times), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=create_back_button(), parse_mode='Markdown')

# التشغيل
if __name__ == "__main__":
    bot.polling()
