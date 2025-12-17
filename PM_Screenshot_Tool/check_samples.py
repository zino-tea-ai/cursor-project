# -*- coding: utf-8 -*-
"""检查数据库中的样本"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
from data.db_manager import get_db

db = get_db()
conn = sqlite3.connect(db.db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 查看Onboarding样本
cursor.execute('''
    SELECT s.filename, s.screen_type, s.naming_cn, s.core_function_cn, s.confidence, p.name as product
    FROM screenshots s
    JOIN products p ON s.product_id = p.id
    WHERE s.screen_type = 'Onboarding'
    ORDER BY p.name, s.filename
''')

rows = cursor.fetchall()
print(f'=== Onboarding样本 ({len(rows)}个) ===')
print()

for row in rows:
    product = row['product']
    filename = row['filename']
    naming = row['naming_cn'] or ''
    conf = row['confidence'] or 0
    print(f"{product:20s} | {filename:20s} | {naming:20s} | conf:{conf:.0%}")

conn.close()



import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
from data.db_manager import get_db

db = get_db()
conn = sqlite3.connect(db.db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 查看Onboarding样本
cursor.execute('''
    SELECT s.filename, s.screen_type, s.naming_cn, s.core_function_cn, s.confidence, p.name as product
    FROM screenshots s
    JOIN products p ON s.product_id = p.id
    WHERE s.screen_type = 'Onboarding'
    ORDER BY p.name, s.filename
''')

rows = cursor.fetchall()
print(f'=== Onboarding样本 ({len(rows)}个) ===')
print()

for row in rows:
    product = row['product']
    filename = row['filename']
    naming = row['naming_cn'] or ''
    conf = row['confidence'] or 0
    print(f"{product:20s} | {filename:20s} | {naming:20s} | conf:{conf:.0%}")

conn.close()



import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
from data.db_manager import get_db

db = get_db()
conn = sqlite3.connect(db.db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 查看Onboarding样本
cursor.execute('''
    SELECT s.filename, s.screen_type, s.naming_cn, s.core_function_cn, s.confidence, p.name as product
    FROM screenshots s
    JOIN products p ON s.product_id = p.id
    WHERE s.screen_type = 'Onboarding'
    ORDER BY p.name, s.filename
''')

rows = cursor.fetchall()
print(f'=== Onboarding样本 ({len(rows)}个) ===')
print()

for row in rows:
    product = row['product']
    filename = row['filename']
    naming = row['naming_cn'] or ''
    conf = row['confidence'] or 0
    print(f"{product:20s} | {filename:20s} | {naming:20s} | conf:{conf:.0%}")

conn.close()



import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
from data.db_manager import get_db

db = get_db()
conn = sqlite3.connect(db.db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 查看Onboarding样本
cursor.execute('''
    SELECT s.filename, s.screen_type, s.naming_cn, s.core_function_cn, s.confidence, p.name as product
    FROM screenshots s
    JOIN products p ON s.product_id = p.id
    WHERE s.screen_type = 'Onboarding'
    ORDER BY p.name, s.filename
''')

rows = cursor.fetchall()
print(f'=== Onboarding样本 ({len(rows)}个) ===')
print()

for row in rows:
    product = row['product']
    filename = row['filename']
    naming = row['naming_cn'] or ''
    conf = row['confidence'] or 0
    print(f"{product:20s} | {filename:20s} | {naming:20s} | conf:{conf:.0%}")

conn.close()



import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
from data.db_manager import get_db

db = get_db()
conn = sqlite3.connect(db.db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 查看Onboarding样本
cursor.execute('''
    SELECT s.filename, s.screen_type, s.naming_cn, s.core_function_cn, s.confidence, p.name as product
    FROM screenshots s
    JOIN products p ON s.product_id = p.id
    WHERE s.screen_type = 'Onboarding'
    ORDER BY p.name, s.filename
''')

rows = cursor.fetchall()
print(f'=== Onboarding样本 ({len(rows)}个) ===')
print()

for row in rows:
    product = row['product']
    filename = row['filename']
    naming = row['naming_cn'] or ''
    conf = row['confidence'] or 0
    print(f"{product:20s} | {filename:20s} | {naming:20s} | conf:{conf:.0%}")

conn.close()



import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
from data.db_manager import get_db

db = get_db()
conn = sqlite3.connect(db.db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 查看Onboarding样本
cursor.execute('''
    SELECT s.filename, s.screen_type, s.naming_cn, s.core_function_cn, s.confidence, p.name as product
    FROM screenshots s
    JOIN products p ON s.product_id = p.id
    WHERE s.screen_type = 'Onboarding'
    ORDER BY p.name, s.filename
''')

rows = cursor.fetchall()
print(f'=== Onboarding样本 ({len(rows)}个) ===')
print()

for row in rows:
    product = row['product']
    filename = row['filename']
    naming = row['naming_cn'] or ''
    conf = row['confidence'] or 0
    print(f"{product:20s} | {filename:20s} | {naming:20s} | conf:{conf:.0%}")

conn.close()

