import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from config import BOT_TOKEN

# ======================
# CONFIG
# ======================
DB_NAME = "files.db"
ALLOWED_EXT = (".pdf", ".xls", ".xlsx", ".jpg", ".jpeg")

# ======================
# STATE
# ======================
USER_STATE = {}
USER_CONTEXT = {}

ASK_YEAR = "ASK_YEAR"
ASK_PROJECT = "ASK_PROJECT"
ASK_CUSTOMER = "ASK_CUSTOMER"
ASK_TITLE = "ASK_TITLE"
ASK_PIC = "ASK_PIC"

# ======================
# DATABASE
# ======================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            telegram_file_id TEXT,
            file_type TEXT,
            uploaded_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_file(name, file_id, file_type):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO files (file_name, telegram_file_id, file_type, uploaded_at)
        VALUES (?, ?, ?, ?)
    """, (name, file_id, file_type, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def search_files(keyword):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT file_name, telegram_file_id, file_type
        FROM files
        WHERE LOWER(file_name) LIKE ?
        ORDER BY uploaded_at DESC
    """, (f"%{keyword.lower()}%",))
    rows = c.fetchall()
    conn.close()
    return rows

# ======================
# COMMANDS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 TSCM File Storage Bot\n\n"
        "📤 Kirim file PDF / Excel / JPG\n"
        "File akan otomatis di-rename\n\n"
        "🔍 Cari file:\n"
        "/search <keyword>\n"
        "/list\n\n"
        "Contoh search:\n"
        "/search 1990\n"
        "/search MAA\n"
        "/search Aveva"
    )

async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Contoh: /search MAA")
        return

    keyword = " ".join(context.args)
    results = search_files(keyword)

    if not results:
        await update.message.reply_text("❌ File tidak ditemukan")
        return

    await update.message.reply_text(f"🔍 Ditemukan {len(results)} file:")

    for name, fid, ftype in results[:10]:
        if ftype == "photo":
            await update.message.reply_photo(photo=fid, caption=name)
        else:
            await update.message.reply_document(document=fid, caption=name)

async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = search_files("")
    if not results:
        await update.message.reply_text("📭 Belum ada file")
        return

    msg = "📂 File Tersimpan:\n\n"
    for r in results[:20]:
        msg += f"• {r[0]}\n"

    await update.message.reply_text(msg)

# ======================
# FILE HANDLER
# ======================
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    doc = update.message.document
    photo = update.message.photo

    if doc:
        if not doc.file_name.lower().endswith(ALLOWED_EXT):
            await update.message.reply_text("❌ Format tidak didukung")
            return

        ext = doc.file_name.split(".")[-1].lower()
        USER_CONTEXT[uid] = {
            "file_id": doc.file_id,
            "ext": ext,
            "type": "document"
        }

    elif photo:
        USER_CONTEXT[uid] = {
            "file_id": photo[-1].file_id,
            "ext": "jpg",
            "type": "photo"
        }
    else:
        return

    USER_STATE[uid] = ASK_YEAR
    await update.message.reply_text("📅 Tahun file? (contoh: 1990 / 2024)")

# ======================
# TEXT STATE HANDLER
# ======================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    state = USER_STATE.get(uid)

    if not state:
        return

    ctx = USER_CONTEXT[uid]

    if state == ASK_YEAR:
        if not text.isdigit() or len(text) != 4:
            await update.message.reply_text("❌ Tahun harus 4 digit (contoh: 1990)")
            return
        ctx["year"] = text
        USER_STATE[uid] = ASK_PROJECT
        await update.message.reply_text("📌 Nama Project?")

    elif state == ASK_PROJECT:
        ctx["project"] = text.replace(" ", "_")
        USER_STATE[uid] = ASK_CUSTOMER
        await update.message.reply_text("🏢 Customer?")

    elif state == ASK_CUSTOMER:
        ctx["customer"] = text.replace(" ", "_")
        USER_STATE[uid] = ASK_TITLE
        await update.message.reply_text("📝 Judul File?")

    elif state == ASK_TITLE:
        ctx["title"] = text.replace(" ", "_")
        USER_STATE[uid] = ASK_PIC
        await update.message.reply_text("👤 PIC?")

    elif state == ASK_PIC:
        ctx["pic"] = text.replace(" ", "_")

        filename = (
            f"{ctx['year']}_{ctx['project']}_{ctx['customer']}_"
            f"{ctx['title']}_{ctx['pic']}.{ctx['ext']}"
        )

        save_file(filename, ctx["file_id"], ctx["type"])

        USER_STATE.pop(uid)
        USER_CONTEXT.pop(uid)

        await update.message.reply_text(
            f"✅ File disimpan sebagai:\n`{filename}`",
            parse_mode="Markdown"
        )

# ======================
# MAIN
# ======================
init_db()

app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("search", search_cmd))
app.add_handler(CommandHandler("list", list_cmd))
app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, file_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("📦 TSCM Storage Bot RUNNING (FINAL & STABLE)")
app.run_polling()
