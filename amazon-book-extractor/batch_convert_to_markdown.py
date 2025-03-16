#!/usr/bin/env python3
"""
批量将提取的书籍JSON文件转换为Markdown格式，以便导入到TheBrain
"""

import json
import os
import argparse
import sys
import glob
from json_to_markdown import json_to_markdown

def main():
    parser = argparse.ArgumentParser(description='批量将提取的书籍JSON文件转换为Markdown格式')
    parser.add_argument('--input', '-i', required=True, help='输入JSON文件路径或匹配模式，例如 "test/*.json"')
    parser.add_argument('--output', '-o', help='输出目录，默认使用输入文件所在目录')
    parser.add_argument('--index', '-idx', action='store_true', help='是否生成索引文件，包含所有图书的链接')
    
    args = parser.parse_args()
    
    # 处理输入文件
    if '*' in args.input or '?' in args.input:
        # 批量处理模式
        json_files = glob.glob(args.input)
        if not json_files:
            print(f"没有找到匹配的文件: {args.input}")
            return
        
        # 确定输出目录
        output_dir = args.output if args.output else os.path.dirname(json_files[0])
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 转换所有文件
        md_files = []
        for json_file in json_files:
            base_name = os.path.splitext(os.path.basename(json_file))[0]
            output_file = os.path.join(output_dir, f"{base_name}.md")
            
            try:
                json_to_markdown(json_file, output_file)
                print(f"成功将 {json_file} 转换为 Markdown 格式: {output_file}")
                md_files.append((output_file, get_book_title(json_file)))
            except Exception as e:
                print(f"转换 {json_file} 时发生错误: {str(e)}")
        
        # 生成索引文件
        if args.index and md_files:
            create_index_file(md_files, output_dir)
    else:
        # 单文件模式
        if not os.path.exists(args.input):
            print(f"文件不存在: {args.input}")
            return
        
        # 确定输出目录和文件
        output_dir = args.output if args.output else os.path.dirname(args.input)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        output_file = os.path.join(output_dir, f"{base_name}.md")
        
        try:
            json_to_markdown(args.input, output_file)
            print(f"成功将 {args.input} 转换为 Markdown 格式: {output_file}")
            
            # 生成索引文件
            if args.index:
                create_index_file([(output_file, get_book_title(args.input))], output_dir)
        except Exception as e:
            print(f"转换 {args.input} 时发生错误: {str(e)}")

def get_book_title(json_file):
    """
    从JSON文件中获取图书标题
    
    Args:
        json_file (str): JSON文件路径
    
    Returns:
        str: 图书标题
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            book_data = json.load(f)
        return book_data.get('书名', os.path.basename(json_file))
    except:
        return os.path.basename(json_file)

def create_index_file(md_files, output_dir):
    """
    创建索引文件，包含所有图书的链接
    
    Args:
        md_files (list): (文件路径, 标题) 元组列表
        output_dir (str): 输出目录
    """
    index_file = os.path.join(output_dir, "图书索引.md")
    
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write("# 图书索引\n\n")
        f.write("以下是所有已转换的图书列表，点击链接查看详细信息：\n\n")
        
        for md_file, title in sorted(md_files, key=lambda x: x[1]):
            rel_path = os.path.relpath(md_file, output_dir)
            f.write(f"- [{title}]({rel_path})\n")
    
    print(f"成功创建索引文件: {index_file}")

if __name__ == "__main__":
    main()
