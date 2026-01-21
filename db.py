def update_project(project_id, field, value):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        f"UPDATE projects SET {field}=? WHERE id=?",
        (value, project_id)
    )
    conn.commit()
    conn.close()
