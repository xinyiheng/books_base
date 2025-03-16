#!/usr/bin/env python3
"""
将提取的书籍JSON文件转换为Markdown格式
"""

import json
import os
import argparse
import sys
import glob

def json_to_markdown(json_file, output_file=None):
    """
    将JSON文件转换为Markdown格式
    
    Args:
        json_file (str): JSON文件路径
        output_file (str, optional): 输出Markdown文件路径。如果不指定，将基于JSON文件名生成
    
    Returns:
        str: 生成的Markdown文件路径
    """
    try:
        # 读取JSON文件
        with open(json_file, 'r', encoding='utf-8') as f:
            book_data = json.load(f)
        
        # 如果未指定输出文件，则基于JSON文件名生成
        if not output_file:
            base_name = os.path.splitext(os.path.basename(json_file))[0]
            output_file = os.path.join(os.path.dirname(json_file), f"{base_name}.md")
        
        # 生成Markdown内容
        md_content = []
        
        # 书名作为标题
        md_content.append(f"# {book_data.get('书名', '')}")
        md_content.append("")
        
        # 添加封面图片（如果有）
        if book_data.get('封面'):
            md_content.append(f"![封面]({book_data.get('封面')})")
            md_content.append("")
        
        # 基本信息表格
        md_content.append("## 基本信息")
        md_content.append("")
        md_content.append("| 项目 | 内容 |")
        md_content.append("| --- | --- |")
        
        # 添加作者信息（带链接）
        author = book_data.get('作者', '')
        author_url = book_data.get('作者页面', '')
        if author and author_url:
            md_content.append(f"| 作者 | [{author}]({author_url}) |")
        else:
            md_content.append(f"| 作者 | {author} |")
        
        # 添加书本页面链接
        book_url = book_data.get('书本页面', '')
        if book_url:
            md_content.append(f"| 书本页面 | [Amazon链接]({book_url}) |")
        
        # 添加其他基本信息
        for key in ['出版社', '出版时间', 'ISBN', '评分']:
            if key in book_data and book_data[key]:
                md_content.append(f"| {key} | {book_data[key]} |")
        
        md_content.append("")
        
        # 内容简介
        if book_data.get('内容简介'):
            md_content.append("## 内容简介")
            md_content.append("")
            md_content.append(book_data.get('内容简介', ''))
            md_content.append("")
        
        # 作者简介
        if book_data.get('作者简介'):
            md_content.append("## 作者简介")
            md_content.append("")
            md_content.append(book_data.get('作者简介', ''))
            md_content.append("")
        
        # 关联图书
        if book_data.get('关联图书'):
            md_content.append("## 关联图书")
            md_content.append("")
            
            related_books = book_data.get('关联图书', [])
            if isinstance(related_books, list):
                for book in related_books:
                    # 尝试从格式为"书名 - URL"的字符串中提取书名和URL
                    if isinstance(book, str) and " - " in book:
                        title, url = book.split(" - ", 1)
                        # 确保URL格式正确
                        url = url.strip()
                        md_content.append(f"- [{title}]({url})")
                    else:
                        md_content.append(f"- {book}")
            elif isinstance(related_books, str):
                # 如果关联图书是字符串，按行分割
                for line in related_books.split('\n'):
                    if " - " in line:
                        title, url = line.split(" - ", 1)
                        # 确保URL格式正确
                        url = url.strip()
                        md_content.append(f"- [{title}]({url})")
                    else:
                        md_content.append(f"- {line}")
            
            md_content.append("")
        
        # 读者评论
        if book_data.get('读者评论'):
            md_content.append("## 读者评论")
            md_content.append("")
            
            reviews = book_data.get('读者评论', [])
            if isinstance(reviews, list):
                for i, review in enumerate(reviews, 1):
                    md_content.append(f"### 评论 {i}")
                    
                    if isinstance(review, dict):
                        reviewer = review.get('reviewer_name', '匿名')
                        rating = review.get('rating', '')
                        title = review.get('title', '')
                        content = review.get('content', '')
                        date = review.get('date', '')
                        
                        if reviewer and rating:
                            md_content.append(f"**{reviewer}** ({rating}星)")
                        elif reviewer:
                            md_content.append(f"**{reviewer}**")
                        
                        if title:
                            md_content.append(f"*{title}*")
                        
                        if content:
                            md_content.append(f"{content}")
                        
                        if date:
                            md_content.append(f"*{date}*")
                    else:
                        md_content.append(f"{review}")
                    
                    md_content.append("")
            elif isinstance(reviews, str):
                md_content.append(reviews)
                md_content.append("")
        
        # 写入Markdown文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_content))
        
        print(f"成功将 {json_file} 转换为 Markdown 格式: {output_file}")
        return output_file
    
    except Exception as e:
        print(f"转换过程中发生错误: {str(e)}", file=sys.stderr)
        return None

# 为了兼容性，创建一个别名函数
def convert_to_markdown(book_data):
    """
    将书籍数据转换为Markdown格式
    
    Args:
        book_data (dict): 书籍数据字典
    
    Returns:
        str: Markdown格式的内容
    """
    # 生成Markdown内容
    md_content = []
    
    # 书名作为标题
    md_content.append(f"# {book_data.get('书名', '')}")
    md_content.append("")
    
    # 添加封面图片（如果有）
    if book_data.get('封面'):
        md_content.append(f"![封面]({book_data.get('封面')})")
        md_content.append("")
    
    # 基本信息表格
    md_content.append("## 基本信息")
    md_content.append("")
    md_content.append("| 项目 | 内容 |")
    md_content.append("| --- | --- |")
    
    # 添加基本信息字段
    for key, value in book_data.items():
        if key != '封面' and key != '书名' and key != '详情' and key != 'URL' and key != '关联图书' and key != '读者评论':
            md_content.append(f"| {key} | {value} |")
    
    # 添加URL（如果有）
    if book_data.get('URL'):
        md_content.append(f"| 链接 | [{book_data.get('URL')}]({book_data.get('URL')}) |")
    
    # 添加详情（如果有）
    if book_data.get('详情'):
        md_content.append("")
        md_content.append("## 详情")
        md_content.append("")
        md_content.append(book_data.get('详情'))
    
    # 添加关联图书（如果有）
    if book_data.get('关联图书'):
        md_content.append("")
        md_content.append("## 关联图书")
        md_content.append("")
        
        related_books = book_data.get('关联图书')
        if isinstance(related_books, list):
            for book in related_books:
                if isinstance(book, dict) and 'title' in book and 'url' in book:
                    md_content.append(f"- [{book['title']}]({book['url']})")
                elif isinstance(book, str) and ' - ' in book:
                    # 尝试从字符串中提取标题和URL
                    parts = book.split(' - ', 1)
                    if len(parts) == 2 and parts[1].startswith('http'):
                        title = parts[0].strip()
                        url = parts[1].strip()
                        md_content.append(f"- [{title}]({url})")
                    else:
                        md_content.append(f"- {book}")
                else:
                    md_content.append(f"- {book}")
        elif isinstance(related_books, str):
            # 如果是单个字符串，尝试拆分多行
            books = related_books.split('\n')
            for book in books:
                book = book.strip()
                if not book:
                    continue
                    
                if ' - ' in book and 'http' in book:
                    # 尝试从字符串中提取标题和URL
                    parts = book.split(' - ', 1)
                    if len(parts) == 2 and parts[1].startswith('http'):
                        title = parts[0].strip()
                        url = parts[1].strip()
                        md_content.append(f"- [{title}]({url})")
                    else:
                        md_content.append(f"- {book}")
                else:
                    md_content.append(f"- {book}")
    
    # 添加读者评论（如果有）
    if book_data.get('读者评论'):
        md_content.append("")
        md_content.append("## 读者评论")
        md_content.append("")
        
        reviews = book_data.get('读者评论')
        if isinstance(reviews, list):
            for i, review in enumerate(reviews):
                if isinstance(review, dict):
                    md_content.append(f"### 评论 {i+1}")
                    md_content.append("")
                    
                    if 'reviewer_name' in review:
                        md_content.append(f"- **评论者**: {review['reviewer_name']}")
                    
                    if 'rating' in review:
                        md_content.append(f"- **评分**: {review['rating']}")
                    
                    if 'title' in review:
                        md_content.append(f"- **标题**: {review['title']}")
                    
                    if 'date' in review:
                        md_content.append(f"- **日期**: {review['date']}")
                    
                    if 'content' in review:
                        md_content.append(f"- **内容**: {review['content']}")
                    
                    if 'helpful_votes' in review:
                        md_content.append(f"- **有用票数**: {review['helpful_votes']}")
                    
                    md_content.append("")
                else:
                    md_content.append(f"- {review}")
                    md_content.append("")
        elif isinstance(reviews, str):
            # 如果是单个字符串，直接添加
            md_content.append(reviews)
    
    return "\n".join(md_content)

def process_multiple_files(input_pattern, output_dir=None):
    """
    批量处理多个JSON文件
    
    Args:
        input_pattern (str): 输入文件匹配模式，例如 "test/*.json"
        output_dir (str, optional): 输出目录。如果不指定，将使用输入文件所在目录
    
    Returns:
        list: 生成的Markdown文件路径列表
    """
    json_files = glob.glob(input_pattern)
    if not json_files:
        print(f"没有找到匹配的文件: {input_pattern}")
        return []
    
    output_files = []
    for json_file in json_files:
        if output_dir:
            base_name = os.path.splitext(os.path.basename(json_file))[0]
            output_file = os.path.join(output_dir, f"{base_name}.md")
        else:
            output_file = None
        
        result = json_to_markdown(json_file, output_file)
        if result:
            output_files.append(result)
    
    return output_files

def main():
    parser = argparse.ArgumentParser(description='将提取的书籍JSON文件转换为Markdown格式')
    parser.add_argument('--input', '-i', required=True, help='输入JSON文件路径或匹配模式，例如 "test/*.json"')
    parser.add_argument('--output', '-o', help='输出Markdown文件路径（单文件）或输出目录（多文件）')
    parser.add_argument('--batch', '-b', action='store_true', help='批量处理模式，输入参数将被视为文件匹配模式')
    
    args = parser.parse_args()
    
    if args.batch or '*' in args.input or '?' in args.input:
        # 批量处理模式
        output_files = process_multiple_files(args.input, args.output)
        if output_files:
            print(f"成功转换 {len(output_files)} 个文件")
    else:
        # 单文件模式
        json_to_markdown(args.input, args.output)

if __name__ == "__main__":
    main()
