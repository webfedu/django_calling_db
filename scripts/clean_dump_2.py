""" 
Зробити дамп із SQLite: 
sqlite3 db.sqlite3 .dump > dump.sql

Запустити цей скрипт.

Для MySQL виконати команду:
cmd /c "mysql -u root -p --default-character-set=utf8mb4 call_db < dump_mysql_clean.sql" """

import re
import hashlib

# ------------------------------
# Вхідний та вихідний файли
# ------------------------------
input_file = "calling_db/dump_mysql_fixed.sql"
output_file = "calling_db/dump_mysql_clean.sql"

print(f"[INFO] Fixing SQL dump: {input_file}")

with open(input_file, "r", encoding="utf-8") as f:
    sql = f.read()

# ------------------------------
# STEP 1. Заміни синтаксису (SQLite → MySQL)
# ------------------------------
print("[STEP 1] Syntax replacements (SQLite → MySQL)")
replacements = {
    r"\bAUTOINCREMENT\b": "AUTO_INCREMENT",
    r"\bINTEGER PRIMARY KEY\b": "INT NOT NULL AUTO_INCREMENT PRIMARY KEY",
    r"\bDEFERRABLE INITIALLY DEFERRED\b": "",  # несумісний синтаксис
}
for pattern, replacement in replacements.items():
    sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)

# Лапки → бектики
sql = sql.replace('"', '`')

# ------------------------------
# STEP 2. Збільшення всіх VARCHAR ≤ 255 (крім calling_app_holding)
# ------------------------------
print("[STEP 2] Expanding VARCHAR sizes")

def process_varchar(sql_text):
    result = []
    current_table = None
    for line in sql_text.splitlines():
        m = re.search(r"CREATE TABLE\s+`?(\w+)`?", line, flags=re.IGNORECASE)
        if m:
            current_table = m.group(1)
            print(f"  -> Processing table: {current_table}")

        def repl(match):
            size = int(match.group(1))
            if current_table == "calling_app_holding":
                print(f"     [SKIP] {current_table}.VARCHAR({size}) left unchanged")
                return match.group(0)
            if size <= 255:
                new_size = size * 3
                print(f"     [UPDATE] {current_table}.VARCHAR({size}) → VARCHAR({new_size})")
                return f"VARCHAR({new_size})"
            return match.group(0)

        line = re.sub(r"VARCHAR\((\d+)\)", repl, line, flags=re.IGNORECASE)
        result.append(line)
    return "\n".join(result)

sql = process_varchar(sql)

# ------------------------------
# STEP 3. Додаємо DROP TABLE перед CREATE TABLE
# ------------------------------
print("[STEP 3] Adding DROP TABLE IF EXISTS before CREATE TABLE")
sql = re.sub(
    r"(CREATE TABLE\s+`?(\w+)`?)",
    lambda m: f"DROP TABLE IF EXISTS `{m.group(2)}`;\n{m.group(1)}",
    sql,
    flags=re.IGNORECASE
)

# ------------------------------
# STEP 4. Додаємо utf8mb4_unicode_ci для всіх CREATE TABLE
# ------------------------------
print("[STEP 4] Adding UTF8MB4 charset to all tables")
def add_utf8mb4_charset(sql_text):
    def repl(match):
        table_name = match.group(1)
        table_body = match.group(2)
        # прибираємо старі ENGINE/CHARSET
        table_body_clean = re.sub(r"\)\s*ENGINE=.*?;", ")", table_body, flags=re.IGNORECASE | re.DOTALL)
        return f"CREATE TABLE `{table_name}` {table_body_clean} ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
    
    # жадібний match всіх дужок до останньої закриваючої
    return re.sub(
        r"CREATE TABLE\s+`?(\w+)`?\s*(\(.+?\))\s*;",
        repl,
        sql_text,
        flags=re.IGNORECASE | re.DOTALL
    )

sql = add_utf8mb4_charset(sql)

# ------------------------------
# STEP 5. Додаємо INSERT IGNORE для холдингу та регіонів
# ------------------------------
print("[STEP 5] Adding INSERT IGNORE for holdings and regions")
sql = re.sub(r"INSERT INTO `calling_app_holding`", r"INSERT IGNORE INTO `calling_app_holding`", sql)
sql = re.sub(r"INSERT INTO `calling_app_region`", r"INSERT IGNORE INTO `calling_app_region`", sql)

# ------------------------------
# STEP 6. Вимикаємо foreign key перевірки
# ------------------------------
print("[STEP 6] Disabling foreign key checks")
sql = "SET FOREIGN_KEY_CHECKS=0;\n\n" + sql + "\n\nSET FOREIGN_KEY_CHECKS=1;"

# ------------------------------
# STEP 7. Скорочуємо назви індексів > 64 символів
# ------------------------------
print("[STEP 7] Shortening long index names")
def shorten_index_names(sql_text):
    def repl(match):
        full = match.group(0)
        name = match.group(1)
        if len(name) > 64:
            short = name[:40] + "_" + hashlib.md5(name.encode()).hexdigest()[:8]
            print(f"     [FIX] Index name too long ({len(name)}): {name} → {short}")
            return full.replace(name, short)
        return full
    return re.sub(
        r"CREATE (?:UNIQUE )?INDEX `([^`]+)`",
        repl,
        sql_text
    )

sql = shorten_index_names(sql)

# ------------------------------
# STEP 8. Перевірка довгих 'name'
# ------------------------------
print("[STEP 8] Checking long 'name' values")
pattern_name = re.compile(r"`name`\s*=\s*'([^']*)'", flags=re.IGNORECASE)
for match in pattern_name.finditer(sql):
    val = match.group(1)
    if len(val) > 512:
        print(f"[WARNING] Value too long for 'name' ({len(val)} chars): {val[:100]}...")

# ------------------------------
# STEP 9. Виправляємо дублікат 'Active' у status_name
# ------------------------------
print("[STEP 9] Fixing duplicate 'Active' in status_name")
sql = re.sub(r"('Active')", r"'Active_2'", sql)


# ------------------------------
# Крок X. Видаляємо sqlite_sequence
# ------------------------------
print("[STEP X] Remove sqlite_sequence rows")

sql = "\n".join(
    line for line in sql.splitlines()
    if "sqlite_sequence" not in line
)

# ------------------------------
# STEP 10. Запис результату
# ------------------------------
print("[STEP 10] Saving cleaned SQL dump")
with open(output_file, "w", encoding="utf-8") as f:
    f.write(sql)

print(f"[INFO] Fixed dump saved to {output_file}")
