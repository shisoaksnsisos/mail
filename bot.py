import asyncio
import logging
import random
import re
import sqlite3
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CopyTextButton,
    ReactionTypeEmoji,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = "8848052661:AAEYlJkXH7YMUKyOVdaKTNHgoIVFu6WD4d0"

DB_FILE = "emails.db"
MAX_PER_GENERATE = 5
PAGE_SIZE = 5

DEFAULT_DOMAINS = ["gmail.com", "outlook.com", "proton.me", "atomicmail.com"]

# ایموجی‌های معتبر و استاندارد ری‌اکشن تلگرام
REACTION_EMOJIS = {
    "email": ["❤️", "👍", "⚡", "🔥"],
    "platform": ["😈", "📌", "✨", "🎯"],
    "edit_note": ["👍", "⚡", "👌", "🎯", "🔥"],
    "general": ["👍", "⚡", "👀", "🫡"]
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$"
)

WORDS = [
    "sports","gaming","tech","shop","store","movie","music","news","play",
    "pro","vip","plus","club","zone","world","daily","media","web","app",
    "online","market","digital","power","speed","fast","smart","prime",
    "star","gold","blue","green","red","black","white","alpha","beta",
    "gamma","delta","omega","nova","pixel","cloud","code","data","dev",
    "home","live","arena","battle","quest","fun","social","photo","video",
    "stream","film","series","book","read","learn","school","study","work",
    "test","demo","user","member","account","login","register","access",
    "service","deal","offer","promo","bonus","reward","gift","point","score",
    "rank","level","hero","legend","master","king","queen","boss","team",
    "group","fan","elite","max","ultra","mega","super","hyper","turbo",
    "next","future","today","tomorrow","summer","winter","spring","autumn",
]

TEXTS = {
    "fa": {
        "main_menu": (
            "✦ <b>سیستم مدیریت ایمیل‌های مستعار (Alias Manager)</b> ✦\n\n"
            "به سرویس <b>حرفه‌ای</b> ساخت آدرس‌های جایگزین و <b>امن</b> خوش آمدید. ⟡\n\n"
            "با استفاده از این ابزار می‌توانید برای <b>ایمیل اصلی خود</b>، ده‌ها آدرس <b>یک‌بار‌مصرف</b> و <b>اختصاصی</b> ایجاد کنید تا از نفوذ اسپم‌ها به صندوق ورودی جلوگیری کرده و <b>حریم خصوصی</b> خود را در بالاترین سطح حفظ نمایید.\n\n"
            "▫ <i>لطفاً برای شروع عملیات، از منوی زیر استفاده کنید:</i>"
        ),
        "btn_new": "⊞ ساخت ایمیل جدید",
        "btn_saved": "≡ ایمیل‌های ساخته شده",
        "btn_stats": "◱ آمار عملکرد من",
        "btn_change_lang": "🌐 تغییر زبان",
        "btn_home": "⌂ صفحه اصلی",
        "btn_cancel": "✕ لغو عملیات",
        "btn_confirm": "✓ تأیید و ساخت",
        "btn_copy_all": "کپی همه ایمیل‌ها",
        "btn_clear_all": "✕ پاکسازی کل تاریخچه",
        "btn_copy": "کپی ({idx})",
        "default_lbl": "پیش‌فرض",
        "prompt_email": (
            "⊞ <b>پیکربندی آدرس پایه</b>\n\n"
            "لطفاً <b>ایمیل اصلی</b> خود را با دقت ارسال کنید. آدرس‌های جایگزینِ تولید شده، به این ایمیل متصل خواهند شد. ⟡\n\n"
            "▫ <i>قالب استاندارد و مجاز:</i>\n"
            "<code>yourname@example.com</code>"
        ),
        "invalid_email": "✕ <b>فرمت ایمیل نامعتبر است.</b>\nلطفاً یک آدرس استاندارد ارسال کنید.\n▫ مثال: <code>Ali@gmail.com</code>",
        "prompt_domain": (
            "🌐 <b>انتخاب دامنه پایه (Domain Selection)</b>\n\n"
            "دامنه مورد نظر خود را برای تولید آدرس‌های مستعار انتخاب کنید: ⟡"
        ),
        "prompt_platform": (
            "✓ <b>ایمیل و دامنه پایه تأیید شد.</b> ⟡\n\n"
            "لطفاً نام <b>پلتفرم</b>، <b>سایت</b> یا <b>یادداشتی</b> برای این آدرس ارسال کنید (مثلاً: <i>Instagram</i> یا <i>خرید آنلاین</i>).\n\n"
            "▫ <i>در صورتی که نیازی به ثبت یادداشت ندارید، عدد <b>0</b> را ارسال کنید.</i>"
        ),
        "prompt_edit_note": (
            "✎ <b>ویرایش یادداشت / پلتفرم</b>\n\n"
            "لطفاً یادداشت جدیدی برای این آدرس وارد کنید:\n"
            "▫ <i>جهت حذف یادداشت، عدد <b>0</b> را ارسال کنید.</i>"
        ),
        "prompt_count": (
            "⚙ <b>تنظیمات تولید آدرس (Generation Settings)</b>\n\n"
            "یادداشت (<b>{platform}</b>) با موفقیت ثبت شد.\n"
            "اکنون <b>تعداد آدرس‌های مستعاری</b> که نیاز دارید را مشخص کنید. ⟡\n\n"
            "▫ <i>حداکثر ظرفیت تولید در هر نشست: <b>۵ آدرس</b></i>"
        ),
        "no_note": "بدون یادداشت",
        "session_expired": "✕ <b>نشست فعلی منقضی شده است.</b> لطفاً مجدداً تلاش کنید.",
        "gen_success_title": "✓ <b>عملیات با موفقیت پایان یافت</b>",
        "gen_success_desc": "آدرس‌های مستعار شما <b>تولید</b> و در پایگاه داده <b>ثبت</b> شدند. ⟡",
        "base_email_lbl": "آدرس مرجع",
        "note_lbl": "یادداشت",
        "addr_lbl": "آدرس",
        "date_exp_lbl": "تاریخ: {date} | انقضا: {days} روز",
        "copy_all_hint": "<i>با استفاده از دکمه زیر، تمامی آدرس‌ها را به صورت <b>یک‌جا</b> کپی کنید.</i>",
        "archive_empty": "📭 <b>صندوق بایگانی خالی است.</b>\nتا کنون هیچ آدرس مستعاری توسط شما تولید نشده است.",
        "archive_title": "≡ <b>بایگانی آدرس‌های تولید شده</b>",
        "archive_sub": "در این بخش، به <b>تاریخچه</b> و <b>لیست کامل</b> آدرس‌های اختصاصی خود دسترسی دارید. ⟡",
        "page_lbl": "صفحه <b>{page}</b> از <b>{max}</b>",
        "deleted_msg": "✕ آدرس موردنظر با موفقیت حذف شد.",
        "cleared_msg": "✕ تمام تاریخچه شما با موفقیت پاکسازی شد.",
        "cleared_text": "📭 <b>پاکسازی با موفقیت انجام شد.</b>\nتاریخچه آدرس‌های شما به طور کامل از سیستم <b>حذف</b> گردید.",
        "stats_text": (
            "◱ <b>گزارش عملکرد و آمار کاربری</b>\n\n"
            "خلاصه‌ای از وضعیت حساب و فعالیت‌های شما در سیستم:\n\n"
            "▫ مجموع آدرس‌های تولید شده: <b>{total} عدد</b>\n"
            "▫ تولید شده در ۳۰ روز اخیر: <b>{recent} عدد</b>\n"
            "▫ پرکاربردترین پلتفرم: <b>{top_platform}</b>\n\n"
            "<i>برای حفظ امنیت بیشتر، پیشنهاد می‌شود آدرس‌های قدیمی را به صورت دوره‌ای <b>پاکسازی</b> نمایید.</i> ⟡"
        ),
        "select_lang": "🌐 <b>تغییر زبان سیستم / Change System Language</b>\n\nلطفاً زبان مورد نظر خود را انتخاب کنید:",
    },
    "en": {
        "main_menu": (
            "✦ <b>Alias Manager System</b> ✦\n\n"
            "Welcome to the <b>professional</b> alias and <b>secure</b> address creation service. ⟡\n\n"
            "Using this tool, you can create dozens of <b>disposable</b> and <b>dedicated</b> alias addresses for your <b>primary email</b> to block spam and keep your <b>privacy</b> at the highest level.\n\n"
            "▫ <i>Please use the menu below to start:</i>"
        ),
        "btn_new": "⊞ Create New Email",
        "btn_saved": "≡ Saved Emails",
        "btn_stats": "◱ My Statistics",
        "btn_change_lang": "🌐 Change Language",
        "btn_home": "⌂ Home",
        "btn_cancel": "✕ Cancel",
        "btn_confirm": "✓ Confirm & Generate",
        "btn_copy_all": "Copy All Emails",
        "btn_clear_all": "✕ Clear All History",
        "btn_copy": "Copy ({idx})",
        "default_lbl": "Default",
        "prompt_email": (
            "⊞ <b>Base Address Configuration</b>\n\n"
            "Please enter your <b>primary email</b> address carefully. Generated aliases will be linked to this email address. ⟡\n\n"
            "▫ <i>Standard format:</i>\n"
            "<code>yourname@example.com</code>"
        ),
        "invalid_email": "✕ <b>Invalid email format.</b>\nPlease enter a standard email address.\n▫ Example: <code>Ali@gmail.com</code>",
        "prompt_domain": (
            "🌐 <b>Domain Selection</b>\n\n"
            "Please select the base domain for generating your aliases: ⟡"
        ),
        "prompt_platform": (
            "✓ <b>Email & Domain verified.</b> ⟡\n\n"
            "Please enter the <b>platform name</b> or a <b>note</b> for this address (e.g., <i>Instagram</i> or <i>Shopping</i>).\n\n"
            "▫ <i>If you don't need a note, send <b>0</b>.</i>"
        ),
        "prompt_edit_note": (
            "✎ <b>Edit Note / Platform</b>\n\n"
            "Please enter the new note for this address:\n"
            "▫ <i>Send <b>0</b> to clear the note.</i>"
        ),
        "prompt_count": (
            "⚙ <b>Generation Settings</b>\n\n"
            "Note (<b>{platform}</b>) saved successfully.\n"
            "Now select <b>how many aliases</b> you need to generate. ⟡\n\n"
            "▫ <i>Maximum capacity per session: <b>5 addresses</b></i>"
        ),
        "no_note": "No Note",
        "session_expired": "✕ <b>Current session expired.</b> Please try again.",
        "gen_success_title": "✓ <b>Operation Completed Successfully</b>",
        "gen_success_desc": "Your aliases have been <b>generated</b> and <b>saved</b> to the database. ⟡",
        "base_email_lbl": "Base Address",
        "note_lbl": "Note",
        "addr_lbl": "Address",
        "date_exp_lbl": "Date: {date} | Exp: {days} Days",
        "copy_all_hint": "<i>Use the button below to copy all generated addresses <b>at once</b>.</i>",
        "archive_empty": "📭 <b>Archive is empty.</b>\nNo alias addresses have been generated yet.",
        "archive_title": "≡ <b>Generated Addresses Archive</b>",
        "archive_sub": "In this section, you have access to your <b>full history</b> of custom addresses. ⟡",
        "page_lbl": "Page <b>{page}</b> of <b>{max}</b>",
        "deleted_msg": "✕ Address deleted successfully.",
        "cleared_msg": "✕ All history cleared successfully.",
        "cleared_text": "📭 <b>History Cleared.</b>\nYour email history has been completely <b>removed</b> from the database.",
        "stats_text": (
            "◱ <b>User Performance & Statistics</b>\n\n"
            "A summary of your account status and activity:\n\n"
            "▫ Total generated addresses: <b>{total}</b>\n"
            "▫ Created in last 30 days: <b>{recent}</b>\n"
            "▫ Most used platform: <b>{top_platform}</b>\n\n"
            "<i>For better security, it is recommended to <b>periodically clear</b> old addresses.</i> ⟡"
        ),
        "select_lang": "🌐 <b>Change System Language / تغییر زبان سیستم</b>\n\nPlease select your preferred language:",
    }
}

async def delete_user_message_later(bot, chat_id, message_id, delay=30):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

async def set_random_reaction(message, category="general"):
    try:
        emoji = random.choice(REACTION_EMOJIS.get(category, REACTION_EMOJIS["general"]))
        await message.set_reaction(reaction=[ReactionTypeEmoji(emoji)])
    except Exception:
        pass

def db():
    return sqlite3.connect(DB_FILE)

def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                original_email TEXT NOT NULL,
                generated_email TEXT NOT NULL,
                created_at TEXT NOT NULL,
                platform TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                lang TEXT NOT NULL DEFAULT 'fa'
            )
        """)
        try:
            conn.execute("ALTER TABLE emails ADD COLUMN platform TEXT")
        except sqlite3.OperationalError:
            pass

def clean_expired_emails():
    """حذف خودکار ایمیل‌های قدیمی‌تر از ۳۱ روز"""
    with db() as conn:
        exp_date = (datetime.now() - timedelta(days=31)).isoformat()
        conn.execute("DELETE FROM emails WHERE created_at < ?", (exp_date,))

def get_user_lang(user_id):
    with db() as conn:
        row = conn.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)).fetchone()
        if row:
            return row[0]
        return "fa"

def set_user_lang(user_id, lang):
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO users (user_id, lang) VALUES (?, ?)",
            (user_id, lang)
        )

def get_lang(user_id, context):
    if "lang" not in context.user_data:
        context.user_data["lang"] = get_user_lang(user_id)
    return context.user_data["lang"]

def save_email(user_id, original, generated, platform):
    with db() as conn:
        conn.execute(
            """INSERT INTO emails
               (user_id, original_email, generated_email, created_at, platform)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, original, generated, datetime.now().isoformat(), platform)
        )

def update_email_platform(email_id, user_id, new_platform):
    with db() as conn:
        conn.execute(
            "UPDATE emails SET platform=? WHERE id=? AND user_id=?",
            (new_platform, email_id, user_id)
        )

def get_emails(user_id, page=0):
    clean_expired_emails()
    offset = page * PAGE_SIZE
    with db() as conn:
        rows = conn.execute(
            """SELECT id, generated_email, platform, created_at
               FROM emails
               WHERE user_id=?
               ORDER BY id DESC
               LIMIT ? OFFSET ?""",
            (user_id, PAGE_SIZE, offset),
        ).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) FROM emails WHERE user_id=?",
            (user_id,),
        ).fetchone()[0]
    return rows, total

def delete_user_email(email_id, user_id):
    with db() as conn:
        conn.execute(
            "DELETE FROM emails WHERE id=? AND user_id=?",
            (email_id, user_id)
        )

def clear_user_emails(user_id):
    with db() as conn:
        conn.execute(
            "DELETE FROM emails WHERE user_id=?",
            (user_id,)
        )

def get_user_stats(user_id):
    clean_expired_emails()
    with db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM emails WHERE user_id=?",
            (user_id,)
        ).fetchone()[0]

        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        recent = conn.execute(
            "SELECT COUNT(*) FROM emails WHERE user_id=? AND created_at >= ?",
            (user_id, thirty_days_ago)
        ).fetchone()[0]

        row = conn.execute(
            """SELECT platform, COUNT(*) as c
               FROM emails
               WHERE user_id=? AND platform IS NOT NULL AND platform != ''
               GROUP BY platform
               ORDER BY c DESC LIMIT 1""",
            (user_id,)
        ).fetchone()

        top_platform = row[0] if row and row[0] else "-"
    return total, recent, top_platform

def valid_email(email):
    return bool(EMAIL_RE.fullmatch(email.strip()))

def new_tag(used):
    patterns = [
        lambda: random.choice(WORDS),
        lambda: random.choice(WORDS) + str(random.randint(1, 999)),
        lambda: random.choice(WORDS) + random.choice(WORDS),
        lambda: random.choice(WORDS) + "_" + random.choice(WORDS),
        lambda: random.choice(WORDS) + random.choice(["x", "pro", "vip"]),
        lambda: random.choice(WORDS) + "_" + str(random.randint(1, 999)),
    ]
    for _ in range(100):
        tag = random.choice(patterns)().lower()
        if tag not in used:
            used.add(tag)
            return tag
    tag = f"alias{random.randint(10000, 999999)}"
    while tag in used:
        tag = f"alias{random.randint(10000, 999999)}"
    used.add(tag)
    return tag

def make_alias(local_part, domain_part, tag):
    return f"{local_part}+{tag}@{domain_part}"

def home_markup(lang):
    t = TEXTS[lang]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t["btn_new"], style="success", callback_data="new"),
            InlineKeyboardButton(t["btn_saved"], style="primary", callback_data="saved:0"),
        ],
        [
            InlineKeyboardButton(t["btn_stats"], style="danger", callback_data="stats")
        ],
    ])

def stats_markup(lang):
    t = TEXTS[lang]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t["btn_change_lang"], style="success", callback_data="lang_menu")
        ],
        [
            InlineKeyboardButton(t["btn_home"], style="danger", callback_data="home")
        ]
    ])

def lang_selection_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇮🇷 فارسی", callback_data="set_lang:fa"),
            InlineKeyboardButton("🇬🇧 English", callback_data="set_lang:en"),
        ]
    ])

def domain_markup(original_domain, lang):
    t = TEXTS[lang]
    def_lbl = t["default_lbl"]
    buttons = [
        [InlineKeyboardButton(f"▫ {original_domain} ({def_lbl})", style="success", callback_data=f"set_domain:{original_domain}")]
    ]
    other_domains = [d for d in DEFAULT_DOMAINS if d != original_domain]
    
    row = []
    for d in other_domains:
        row.append(InlineKeyboardButton(f"@{d}", style="primary", callback_data=f"set_domain:{d}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
        
    buttons.append([InlineKeyboardButton(t["btn_cancel"], style="danger", callback_data="home")])
    return InlineKeyboardMarkup(buttons)

def count_markup(count, lang):
    t = TEXTS[lang]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("−", style="danger", callback_data="minus"),
            InlineKeyboardButton(f"▫ {count} ▫", callback_data="noop"),
            InlineKeyboardButton("+", style="success", callback_data="plus"),
        ],
        [InlineKeyboardButton(t["btn_confirm"], style="primary", callback_data="generate")],
        [InlineKeyboardButton(t["btn_home"], style="danger", callback_data="home")],
    ])

def generated_markup(emails, lang):
    t = TEXTS[lang]
    all_emails_text = "\n".join(emails)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                t["btn_copy_all"],
                style="primary",
                copy_text=CopyTextButton(text=all_emails_text),
            )
        ],
        [
            InlineKeyboardButton(t["btn_home"], style="danger", callback_data="home")
        ]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_lang = get_lang(user_id, context)
    
    context.user_data.clear()
    context.user_data["lang"] = current_lang

    t = TEXTS[current_lang]
    if update.message:
        # پاکسازی خودکار پیام /start کاربر پس از ۳۰ ثانیه و تنظیم ری‌اکشن
        asyncio.create_task(
            delete_user_message_later(
                context.bot, update.effective_chat.id, update.message.message_id, 30
            )
        )
        await set_random_reaction(update.message, "general")

        await update.message.reply_text(
            t["main_menu"], parse_mode="HTML", reply_markup=home_markup(current_lang)
        )
    else:
        await update.callback_query.edit_message_text(
            t["main_menu"], parse_mode="HTML", reply_markup=home_markup(current_lang)
        )

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang(user_id, context)
    t = TEXTS[lang]
    state = context.user_data.get("state")
    
    # 1. دریافت ایمیل اصلی
    if state == "waiting_email":
        email = update.message.text.strip()

        if not valid_email(email):
            await update.message.reply_text(
                t["invalid_email"],
                parse_mode="HTML",
            )
            return

        await set_random_reaction(update.message, "email")

        local_part, domain_part = email.rsplit("@", 1)
        context.user_data["local"] = local_part
        context.user_data["selected_domain"] = domain_part
        context.user_data["original_email"] = email
        context.user_data["state"] = "waiting_domain"
        
        prompt_id = context.user_data.pop("prompt_message_id", None)
        if prompt_id:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=prompt_id,
                )
            except Exception:
                pass

        sent = await update.effective_chat.send_message(
            t["prompt_domain"],
            parse_mode="HTML",
            reply_markup=domain_markup(domain_part, lang)
        )
        context.user_data["prompt_message_id"] = sent.message_id
        return

    # 2. دریافت پلتفرم/یادداشت
    elif state == "waiting_platform":
        platform = update.message.text.strip()
        await set_random_reaction(update.message, "platform")

        if platform == "0":
            platform = t["no_note"]

        context.user_data["platform"] = platform
        context.user_data["count"] = 1
        context.user_data["state"] = "count"

        prompt_id = context.user_data.pop("prompt_message_id", None)
        if prompt_id:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=prompt_id,
                )
            except Exception:
                pass

        await update.effective_chat.send_message(
            t["prompt_count"].format(platform=platform),
            parse_mode="HTML",
            reply_markup=count_markup(1, lang),
        )
        return

    # 3. ویرایش یادداشت
    elif state and state.startswith("edit_note:"):
        parts = state.split(":")
        email_id = int(parts[1])
        page = int(parts[2])

        await set_random_reaction(update.message, "edit_note")

        new_platform = update.message.text.strip()
        if new_platform == "0":
            new_platform = t["no_note"]

        update_email_platform(email_id, user_id, new_platform)
        context.user_data["state"] = None

        prompt_id = context.user_data.pop("prompt_message_id", None)
        if prompt_id:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=prompt_id,
                )
            except Exception:
                pass

        await show_saved(update, context, page)
        return

    else:
        await set_random_reaction(update.message, "general")

async def generate(update, context):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    lang = get_lang(user_id, context)
    t = TEXTS[lang]

    local = context.user_data.get("local")
    domain = context.user_data.get("selected_domain")
    platform = context.user_data.get("platform", t["no_note"])
    count = context.user_data.get("count", 1)

    if not local or not domain:
        await query.edit_message_text(
            t["session_expired"],
            parse_mode="HTML",
            reply_markup=home_markup(lang),
        )
        return

    try:
        await query.message.delete()
    except Exception:
        pass

    used = set()
    result = []
    base_address = f"{local}@{domain}"

    for _ in range(count):
        alias = make_alias(local, domain, new_tag(used))
        result.append(alias)
        save_email(user_id, base_address, alias, platform)

    context.user_data["generated"] = result
    context.user_data["state"] = None

    lines = [
        t["gen_success_title"], 
        "",
        t["gen_success_desc"], 
        f"▫ {t['base_email_lbl']}: <code>{base_address}</code>",
        f"▫ {t['note_lbl']}: <b>{platform}</b>",
        ""
    ]
    for i, email in enumerate(result, 1):
        lines.append(f"<b>{t['addr_lbl']} ({i})</b>\n<code>{email}</code>\n")
    lines.append(t["copy_all_hint"])

    await update.effective_chat.send_message(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=generated_markup(result, lang),
    )

async def show_saved(update, context, page):
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    lang = get_lang(user_id, context)
    t = TEXTS[lang]

    rows, total = get_emails(user_id, page)

    if not total:
        text = t["archive_empty"]
        markup = InlineKeyboardMarkup([[
            InlineKeyboardButton(t["btn_home"], style="danger", callback_data="home")
        ]])
        if query:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
        else:
            await update.effective_chat.send_message(text, parse_mode="HTML", reply_markup=markup)
        return

    start_num = page * PAGE_SIZE + 1
    max_page = max(0, (total - 1) // PAGE_SIZE)

    lines = [
        t["archive_title"],
        t["archive_sub"],
        "",
        f"▫ {t['page_lbl'].format(page=page+1, max=max_page+1)}",
        "",
    ]

    buttons = []
    for idx, row in enumerate(rows, start_num):
        email_id, email, platform, created_at = row
        p_text = platform if platform else t["no_note"]

        # محاسبه روزهای باقی‌مانده از مهلت ۳۱ روزه
        try:
            created_dt = datetime.fromisoformat(created_at)
            date_str = created_dt.strftime("%Y/%m/%d")
            elapsed_days = (datetime.now() - created_dt).days
            days_left = max(0, 31 - elapsed_days)
        except Exception:
            date_str = "N/A"
            days_left = 31

        date_exp_text = t["date_exp_lbl"].format(date=date_str, days=days_left)

        lines.append(
            f"<b>{t['addr_lbl']} ({idx})</b> | 🏷 <i>{p_text}</i>\n"
            f"<b>{date_exp_text}</b>\n"
            f"<code>{email}</code>\n"
        )

        buttons.append([
            InlineKeyboardButton(
                t["btn_copy"].format(idx=idx),
                style="primary",
                copy_text=CopyTextButton(text=email),
            ),
            InlineKeyboardButton(
                "✎",
                style="success",
                callback_data=f"edit_note:{email_id}:{page}"
            ),
            InlineKeyboardButton(
                "✕",
                style="danger",
                callback_data=f"del:{email_id}:{page}"
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◴", style="primary", callback_data=f"saved:{page-1}"))
    if page < max_page:
        nav.append(InlineKeyboardButton("◵", style="primary", callback_data=f"saved:{page+1}"))
    
    if nav:
        buttons.append(nav)

    buttons.append([
        InlineKeyboardButton(t["btn_clear_all"], style="danger", callback_data="clear_all")
    ])
    buttons.append([
        InlineKeyboardButton(t["btn_home"], style="danger", callback_data="home")
    ])

    text_content = "\n".join(lines)
    reply_markup = InlineKeyboardMarkup(buttons)

    if query:
        await query.edit_message_text(text_content, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await update.effective_chat.send_message(text_content, parse_mode="HTML", reply_markup=reply_markup)

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    lang = get_lang(user_id, context)
    t = TEXTS[lang]

    if data == "home":
        await query.answer()
        context.user_data.clear()
        context.user_data["lang"] = lang
        await query.edit_message_text(
            t["main_menu"],
            parse_mode="HTML",
            reply_markup=home_markup(lang),
        )
        return

    if data == "stats":
        await query.answer()
        total, recent, top_platform = get_user_stats(user_id)
        
        await query.edit_message_text(
            t["stats_text"].format(
                total=total,
                recent=recent,
                top_platform=top_platform
            ),
            parse_mode="HTML",
            reply_markup=stats_markup(lang),
        )
        return

    if data == "lang_menu":
        await query.answer()
        await query.edit_message_text(
            t["select_lang"],
            parse_mode="HTML",
            reply_markup=lang_selection_markup(),
        )
        return

    if data.startswith("set_lang:"):
        new_lang = data.split(":")[1]
        set_user_lang(user_id, new_lang)
        context.user_data["lang"] = new_lang
        await query.answer()
        
        try:
            await query.message.delete()
        except Exception:
            pass
            
        new_t = TEXTS[new_lang]
        context.user_data.clear()
        context.user_data["lang"] = new_lang
        
        await update.effective_chat.send_message(
            new_t["main_menu"],
            parse_mode="HTML",
            reply_markup=home_markup(new_lang),
        )
        return

    if data == "new":
        await query.answer()
        context.user_data.clear()
        context.user_data["lang"] = lang
        context.user_data["state"] = "waiting_email"
        
        sent = await query.edit_message_text(
            t["prompt_email"],
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t["btn_cancel"], style="danger", callback_data="home")
            ]]),
        )
        context.user_data["prompt_message_id"] = sent.message_id
        return

    if data.startswith("set_domain:"):
        selected_domain = data.split(":", 1)[1]
        context.user_data["selected_domain"] = selected_domain
        context.user_data["state"] = "waiting_platform"
        await query.answer()

        sent = await query.edit_message_text(
            t["prompt_platform"],
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t["btn_cancel"], style="danger", callback_data="home")
            ]])
        )
        context.user_data["prompt_message_id"] = sent.message_id
        return

    if data.startswith("edit_note:"):
        parts = data.split(":")
        email_id = parts[1]
        page = parts[2]
        
        context.user_data["state"] = f"edit_note:{email_id}:{page}"
        await query.answer()
        
        sent = await query.edit_message_text(
            t["prompt_edit_note"],
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t["btn_cancel"], style="danger", callback_data="home")
            ]])
        )
        context.user_data["prompt_message_id"] = sent.message_id
        return

    if data == "plus":
        current = context.user_data.get("count", 1)
        context.user_data["count"] = min(MAX_PER_GENERATE, current + 1)
        await query.answer()
        await query.edit_message_reply_markup(
            reply_markup=count_markup(context.user_data["count"], lang)
        )
        return

    if data == "minus":
        current = context.user_data.get("count", 1)
        context.user_data["count"] = max(1, current - 1)
        await query.answer()
        await query.edit_message_reply_markup(
            reply_markup=count_markup(context.user_data["count"], lang)
        )
        return

    if data == "noop":
        await query.answer(f"Selected: {context.user_data.get('count', 1)}")
        return

    if data == "generate":
        await generate(update, context)
        return

    if data.startswith("saved:"):
        try:
            page = int(data.split(":", 1)[1])
        except ValueError:
            page = 0
        await show_saved(update, context, page)
        return

    if data.startswith("del:"):
        parts = data.split(":")
        email_id = int(parts[1])
        page = int(parts[2])
        
        delete_user_email(email_id, user_id)
        await query.answer(t["deleted_msg"])
        await show_saved(update, context, page)
        return

    if data == "clear_all":
        clear_user_emails(user_id)
        await query.answer(t["cleared_msg"])
        await query.edit_message_text(
            t["cleared_text"],
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t["btn_home"], style="danger", callback_data="home")
            ]]),
        )
        return

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        asyncio.create_task(
            delete_user_message_later(
                context.bot, update.effective_chat.id, update.message.message_id, 30
            )
        )

    user_id = update.effective_user.id
    lang = get_lang(user_id, context)
    t = TEXTS[lang]
    
    state = context.user_data.get("state")
    if state in ["waiting_email", "waiting_platform"] or (state and state.startswith("edit_note:")):
        await receive_text(update, context)
    else:
        await set_random_reaction(update.message, "general")
        await update.message.reply_text(
            t["main_menu"],
            parse_mode="HTML",
            reply_markup=home_markup(lang),
        )

def main():
    init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)
    )

    print("Bot started successfully.")
    app.run_polling()

if __name__ == "__main__":
    main()
