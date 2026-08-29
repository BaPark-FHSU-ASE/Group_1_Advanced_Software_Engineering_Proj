from app.db.connection import get_connection
from app.models.owner import Owner

# Get all owners
def get_all():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM owners").fetchall()
    conn.close()

    return [Owner.from_row(row) for row in rows]