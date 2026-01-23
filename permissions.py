from config import SUPER_ADMIN_IDS
from db import connect

def is_super_admin(telegram_user_id):
    return telegram_user_id in SUPER_ADMIN_IDS

def is_project_admin(telegram_user_id, project_id):
    if is_super_admin(telegram_user_id):
        return True

    conn = connect()
    c = conn.cursor()

    c.execute("""
        SELECT pic_user_id, status
        FROM projects
        WHERE id=?
    """, (project_id,))

    row = c.fetchone()
    conn.close()

    if not row:
        return False

    pic_user_id, status = row

    return telegram_user_id == pic_user_id and status != "Completed"
