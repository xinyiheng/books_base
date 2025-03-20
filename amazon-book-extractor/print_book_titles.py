#!/usr/bin/env python3
import json

# 打开JSON文件
with open('douban_second_brain.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 获取关联图书列表
related_books = data.get('关联图书', [])

# 打印每本书的标题
print(f"找到{len(related_books)}本关联图书:")
for i, book in enumerate(related_books, 1):
    title = book.get('title', 'Unknown Title')
    print(f"{i}. {title}")

# 计算其他版本图书的数量
other_versions = [book for book in related_books if '(本书的其他版本)' in book.get('title', '')]
print(f"\n其中其他版本图书: {len(other_versions)}本")
if other_versions:
    print("其他版本图书包括:")
    for i, book in enumerate(other_versions, 1):
        title = book.get('title', 'Unknown Title')
        url = book.get('url', 'No URL')
        print(f"{i}. {title} - {url}") 