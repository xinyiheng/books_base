#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from amazon_feishu_extractor import extract_uk_book_info

# 寻找英国站点的HTML文件
uk_html_files = []
for root, dirs, files in os.walk("amazonbooks/html"):
    for file in files:
        if file.endswith(".html") and any(domain in file for domain in ["0241716101", "1916356621", "1786788985"]):
            uk_html_files.append(os.path.join(root, file))

if not uk_html_files:
    print("错误：找不到英国站点的HTML文件")
    exit(1)

# 使用找到的第一个英国HTML文件
html_file_path = uk_html_files[0]

# 读取HTML文件内容
with open(html_file_path, 'r', encoding='utf-8') as file:
    html_content = file.read()

# 使用extract_uk_book_info函数提取信息
print(f"开始处理文件：{html_file_path}")
book_info = extract_uk_book_info(html_content, file_name=html_file_path)

# 打印结果
print("\n==== 提取结果 ====")
for key, value in book_info.items():
    if key != '关联图书' and key != '读者评论' and key != '内容简介' and key != '作者简介':
        print(f"{key}: {value}")
    elif key == '关联图书' and value:
        print(f"{key}: 找到 {len(value)} 本关联图书")
    elif key == '读者评论' and value:
        print(f"{key}: 找到 {len(value)} 条评论")
    elif key in ['内容简介', '作者简介'] and value:
        print(f"{key}: {value[:50]}... (已截断)")

print("\n测试完成！") 