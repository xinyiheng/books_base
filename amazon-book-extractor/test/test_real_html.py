#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from amazon_feishu_extractor import extract_jp_book_info

# 指定HTML文件路径
html_file_path = "amazonbooks/html/amazon_book_4295410306_世界の一流は「休日」に何をしているのか_2025-03-19T01-52-50-980Z.html"

# 确保文件存在
if not os.path.exists(html_file_path):
    print(f"错误：文件不存在 - {html_file_path}")
    exit(1)

# 读取HTML文件内容
with open(html_file_path, 'r', encoding='utf-8') as file:
    html_content = file.read()

# 使用extract_jp_book_info函数提取信息
print(f"开始处理文件：{html_file_path}")
book_info = extract_jp_book_info(html_content, file_name=html_file_path)

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