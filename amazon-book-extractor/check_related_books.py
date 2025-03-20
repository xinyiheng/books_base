#!/usr/bin/env python3
import json
import sys

def check_related_books(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    related_books = data.get("关联图书", [])
    print(f"关联图书总数: {len(related_books)}本")
    
    # 查找其他版本图书
    version_books = [book for book in related_books if "(本书的其他版本)" in book.get("title", "")]
    print(f"其中其他版本图书: {len(version_books)}本")
    
    # 显示其他版本图书
    if version_books:
        print("\n其他版本图书:")
        for i, book in enumerate(version_books, 1):
            print(f"{i}. {book.get('title', '')}")
            print(f"   链接: {book.get('url', '')}")
            print()
    else:
        print("\n未找到其他版本图书")
    
    # 显示普通关联图书
    normal_books = [book for book in related_books if "(本书的其他版本)" not in book.get("title", "")]
    if normal_books:
        print("\n普通关联图书:")
        for i, book in enumerate(normal_books, 1):
            print(f"{i}. {book.get('title', '')} - {book.get('url', '')}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"用法: {sys.argv[0]} json文件路径")
        sys.exit(1)
    
    check_related_books(sys.argv[1]) 