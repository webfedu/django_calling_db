import sqlite3
import os

# Отримати шлях до директорії скрипта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(BASE_DIR)

old_db = os.path.join(BASE_DIR, "old_db.sqlite3")
new_db = os.path.join(BASE_DIR, "db.sqlite3")

old_conn = sqlite3.connect(old_db)
new_conn = sqlite3.connect(new_db)

old_cur = old_conn.cursor()
new_cur = new_conn.cursor()


def migrate_holdings():
    old_cur.execute("SELECT id, name FROM holdings")
    for oid, name in old_cur.fetchall():
        new_cur.execute(
            "INSERT OR IGNORE INTO calling_app_holding (id, name) VALUES (?, ?)",
            (oid, name)
        )
    new_conn.commit()


def migrate_companies():
    old_cur.execute("SELECT id, edrpou, name, address, area_ha, holding_id FROM companies")
    for oid, edrpou, name, addr, ha, hid in old_cur.fetchall():
        new_cur.execute(
            """INSERT OR IGNORE INTO calling_app_company
               (id, edrpou, name, legal_address, hectares, holding_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (oid, edrpou, name, addr, ha, hid)
        )
    new_conn.commit()


def migrate_persons():
    old_cur.execute("SELECT id, full_name, position  FROM persons")
    for pid, fn, p in old_cur.fetchall():
        new_cur.execute(
            "INSERT OR IGNORE INTO calling_app_contactperson (id, full_name, position) VALUES (?, ?, ?)",
            (pid, fn, p)
        )
    new_conn.commit()


    
def link_persons_to_companies():
    old_cur.execute("SELECT company_id, person_id FROM company_persons")
    for company_id, person_id in old_cur.fetchall():
        new_cur.execute(
            "INSERT OR IGNORE INTO calling_app_contactperson_companies (company_id,  contactperson_id) VALUES (?, ?)",
            (company_id, person_id)
        )
    new_conn.commit()


def migrate_phones():
    old_cur.execute("SELECT id, phone_number, status FROM phones")
    for oid, number, status in old_cur.fetchall():
        new_cur.execute(
            """INSERT OR IGNORE INTO calling_app_phone
               (id, number, status, contact_id)
               VALUES (?, ?, ?, NULL)""",
            (oid, number, status or "on")
        )
    new_conn.commit()


def link_phones_to_persons():
    old_cur.execute("SELECT person_id, phone_id FROM persons_phones")
    for person_id, phone_id in old_cur.fetchall():
        new_cur.execute(
            "UPDATE calling_app_phone SET contact_id=? WHERE id=?",
            (person_id, phone_id)
        )
    new_conn.commit()


def link_phones_to_companies():
    old_cur.execute("SELECT company_id, phone_id FROM company_phones")
    for company_id, phone_id in old_cur.fetchall():
        new_cur.execute(
            "INSERT OR IGNORE INTO calling_app_phone_companies (phone_id, company_id) VALUES (?, ?)",
            (phone_id, company_id)
        )
    new_conn.commit()


def migrate_calls():
    old_cur.execute("SELECT id, phone_id, timestamp, notes FROM call_history")
    for oid, phone_id, dt, notes in old_cur.fetchall():
        # треба знайти компанію через company_phones
        old_cur.execute("SELECT company_id FROM company_phones WHERE phone_id=?", (phone_id,))
        row = old_cur.fetchone()
        company_id = row[0] if row else None

        if company_id:
            new_cur.execute(
                """INSERT OR IGNORE INTO calling_app_call
                   (id, phone_id, company_id, datetime, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (oid, phone_id, company_id, dt, notes)
            )
    new_conn.commit()


def main():
    migrate_holdings()
    migrate_companies()
    migrate_persons()
    link_persons_to_companies()
    migrate_phones()
    link_phones_to_persons()
    link_phones_to_companies()
    migrate_calls()
    print("✅ Міграція завершена!")


if __name__ == "__main__":
    main()
