import sqlite3
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram import Update
from config import BOT_TOKEN

# ======================
# DATABASE
# ======================
DB_NAME = "project_management.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            customer TEXT,
            status TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS project_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            file_name TEXT,
            file_type TEXT,
            telegram_file_id TEXT
        )
    """)

    conn.commit()
    conn.close()

def add_project(name, customer):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO projects (name, customer, status) VALUES (?, ?, ?)",
        (name, customer, "Not Started")
    )
    conn.commit()
    conn.close()

def list_projects():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, status FROM projects")
    rows = c.fetchall()
    conn.close()
    return rows

def update_project(project_id, field, value):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        f"UPDATE projects SET {field}=? WHERE id=?",
        (value, project_id)
    )
    conn.commit()
    conn.close()

def delete_project(project_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM projects WHERE id=?", (project_id,))
    conn.commit()
    conn.close()

def save_file(project_id, file_name, file_type, telegram_file_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO project_files (project_id, file_name, file_type, telegram_file_id)
        VALUES (?, ?, ?, ?)
    """, (project_id, file_name, file_type, telegram_file_id))
    conn.commit()
    conn.close()

def search_files(keyword):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT file_name, telegram_file_id
        FROM project_files
        WHERE file_name LIKE ?
    """, (f"%{keyword}%",))
    rows = c.fetchall()
    conn.close()
    return rows

# ======================
# STATE MACHINE
# ======================
USER_STATE = {}
USER_CONTEXT = {}

ADD_PROJECT_NAME = "ADD_PROJECT_NAME"
ADD_PROJECT_CUSTOMER = "ADD_PROJECT_CUSTOMER"

EDIT_PROJECT_CHOOSE_FIELD = "EDIT_PROJECT_CHOOSE_FIELD"
EDIT_PROJECT_NEW_VALUE = "EDIT_PROJECT_NEW_VALUE"

DELETE_PROJECT_CONFIRM = "DELETE_PROJECT_CONFIRM"

UPLOAD_FILE_PROJECT = "UPLOAD_FILE_PROJECT"
SEARCH_FILE = "SEARCH_FILE"

ALLOWED_EXT = (".pdf", ".xls", ".xlsx")

# ======================
# COMMAND HANDLERS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 TSCM Project Monitor Bot\n\n"
        "/addproject - Tambah project\n"
        "/projects - List project\n"
        "/edit <id> - Edit project\n"
        "/delete <id> - Hapus project\n"
        "/search - Cari file\n\n"
        "📄 Kirim PDF / Excel untuk upload file"
    )

async def addproject_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    USER_STATE[user_id] = ADD_PROJECT_NAME
    USER_CONTEXT[user_id] = {}
    await update.message.reply_text("📌 Nama project?")

async def projects_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    projects = list_projects()
    if not projects:
        await update.message.reply_text("📭 Belum ada project.")
        return

    msg = "📋 List Project:\n\n"
    for p in projects:
        msg += f"{p[0]}. {p[1]} ({p[2]})\n"
    await update.message.reply_text(msg)

async def editproject_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Gunakan: /edit <project_id>")
        return

    user_id = update.effective_user.id
    USER_CONTEXT[user_id] = {"project_id": context.args[0]}
    USER_STATE[user_id] = EDIT_PROJECT_CHOOSE_FIELD

    await update.message.reply_text(
        "✏️ Mau ubah apa?\n"
        "Ketik salah satu:\n"
        "name / customer / status"
    )

async def deleteproject_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Gunakan: /delete <project_id>")
        return

    user_id = update.effective_user.id
    USER_CONTEXT[user_id] = {"project_id": context.args[0]}
    USER_STATE[user_id] = DELETE_PROJECT_CONFIRM

    await update.message.reply_text(
        f"⚠️ Yakin hapus project ID {context.args[0]}?\n"
        "Ketik YES untuk lanjut"
    )

async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USER_STATE[update.effective_user.id] = SEARCH_FILE
    await update.message.reply_text("🔍 Cari file apa?")

# ======================
# FILE HANDLER
# ======================
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc:
        return

    if not doc.file_name.lower().endswith(ALLOWED_EXT):
        await update.message.reply_text("❌ Hanya PDF & Excel yang diperbolehkan")
        return

    user_id = update.effective_user.id
    USER_STATE[user_id] = UPLOAD_FILE_PROJECT
    USER_CONTEXT[user_id] = {
        "file_name": doc.file_name,
        "telegram_file_id": doc.file_id
    }

    await update.message.reply_text("📁 File ini untuk project ID berapa?")

# ======================
# TEXT HANDLER (ALL STATE)
# ======================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    state = USER_STATE.get(user_id)

    if state == ADD_PROJECT_NAME:
        USER_CONTEXT[user_id]["name"] = text
        USER_STATE[user_id] = ADD_PROJECT_CUSTOMER
        await update.message.reply_text("🏢 Nama customer?")

    elif state == ADD_PROJECT_CUSTOMER:
        add_project(USER_CONTEXT[user_id]["name"], text)
        USER_STATE.pop(user_id)
        USER_CONTEXT.pop(user_id)
        await update.message.reply_text("✅ Project berhasil ditambahkan")

    elif state == EDIT_PROJECT_CHOOSE_FIELD:
        if text not in ["name", "customer", "status"]:
            await update.message.reply_text("❌ Pilih: name / customer / status")
            return
        USER_CONTEXT[user_id]["field"] = text
        USER_STATE[user_id] = EDIT_PROJECT_NEW_VALUE
        await update.message.reply_text("✏️ Masukkan nilai baru:")

    elif state == EDIT_PROJECT_NEW_VALUE:
        update_project(
            USER_CONTEXT[user_id]["project_id"],
            USER_CONTEXT[user_id]["field"],
            text
        )
        USER_STATE.pop(user_id)
        USER_CONTEXT.pop(user_id)
        await update.message.reply_text("✅ Project berhasil di-update")

    elif state == DELETE_PROJECT_CONFIRM:
        if text == "YES":
            delete_project(USER_CONTEXT[user_id]["project_id"])
            await update.message.reply_text("🗑️ Project berhasil dihapus")
        else:
            await update.message.reply_text("❌ Dibatalkan")
        USER_STATE.pop(user_id)
        USER_CONTEXT.pop(user_id)

    elif state == UPLOAD_FILE_PROJECT:
        data = USER_CONTEXT[user_id]
        save_file(
            text,
            data["file_name"],
            "pdf" if data["file_name"].endswith(".pdf") else "excel",
            data["telegram_file_id"]
        )
        USER_STATE.pop(user_id)
        USER_CONTEXT.pop(user_id)
        await update.message.reply_text("✅ File berhasil disimpan")

    elif state == SEARCH_FILE:
        keyword = text.lower().strip()
        keyword = keyword.replace(" ", "%")

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""
            SELECT file_name, telegram_file_id
            FROM project_files
            WHERE LOWER(file_name) LIKE ?
        """, (f"%{keyword}%",))
        rows = c.fetchall()
        conn.close()

        if not rows:
            await update.message.reply_text("❌ File tidak ditemukan")
        else:
            await update.message.reply_text(f"🔍 Ditemukan {len(rows)} file:")
            for r in rows:
                await update.message.reply_document(
                    r[1],
                    caption=f"📄 {r[0]}"
                )

        USER_STATE.pop(user_id, None)

# ======================
# MAIN
# ======================
init_db()

app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addproject", addproject_cmd))
app.add_handler(CommandHandler("projects", projects_cmd))
app.add_handler(CommandHandler("edit", editproject_cmd))
app.add_handler(CommandHandler("delete", deleteproject_cmd))
app.add_handler(CommandHandler("search", search_cmd))

app.add_handler(MessageHandler(filters.Document.ALL, file_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("🤖 Bot running...")
app.run_polling()