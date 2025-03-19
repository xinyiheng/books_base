#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import re
from bs4 import BeautifulSoup

def extract_author_jp(html_content):
    """测试日本亚马逊作者提取逻辑"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 测试原始逻辑
    author_element = soup.select_one('#bylineInfo .author a, #bylineInfo .contributorNameID')
    original_author = ""
    if author_element:
        original_author = author_element.text.strip()
    
    # 测试修复后的逻辑
    fixed_author = ""
    if author_element:
        author_text = author_element.text.strip()
        half_length = len(author_text) // 2
        if half_length > 0 and author_text[:half_length] == author_text[half_length:]:
            fixed_author = author_text[:half_length]
        else:
            fixed_author = author_text
    
    return {
        "original_author": original_author,
        "fixed_author": fixed_author
    }

def main():
    """主函数，用于测试作者提取逻辑"""
    if len(sys.argv) < 2:
        print("用法: python test_author_extraction.py <html文件路径>")
        sys.exit(1)
    
    html_file = sys.argv[1]
    if not os.path.exists(html_file):
        print(f"错误: 文件 {html_file} 不存在")
        sys.exit(1)
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"读取文件时出错: {e}")
        sys.exit(1)
    
    result = extract_author_jp(html_content)
    
    print("\n测试结果:")
    print(f"原始提取的作者: '{result['original_author']}'")
    print(f"修复后的作者: '{result['fixed_author']}'")
    
    if result['original_author'] == result['fixed_author']:
        print("\n结论: 作者名称没有重复，无需修复")
    else:
        print("\n结论: 作者名称有重复，修复成功")

if __name__ == "__main__":
    main() 