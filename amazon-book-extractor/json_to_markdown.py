#!/usr/bin/env python3
"""
将提取的书籍JSON文件转换为Markdown格式
"""

import json
import os
import argparse
import sys
import glob
import re

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
        
        # 获取书名用于生成文件名
        title = book_data.get('标题') or book_data.get('书名') or book_data.get('title', '')
        
        # 如果未指定输出文件，则基于书名生成
        if not output_file:
            # 直接使用JSON文件中的标题或书名
            if title:
                # 清理书名，只保留书名部分，移除文件系统不允许的字符
                clean_title = title
                # 替换文件系统不允许的字符为下划线
                for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
                    clean_title = clean_title.replace(char, '_')
                
                print(f"使用书名作为文件名: {clean_title}")
            else:
                # 如果没有提取到标题，使用ISBN或原文件名
                json_filename = os.path.basename(json_file)
                if json_filename.endswith('.json'):
                    json_filename = json_filename[:-5]  # 去掉.json扩展名
                
                # 检查是否有ISBN可用
                isbn = book_data.get('ISBN', book_data.get('isbn', ''))
                if isbn:
                    clean_title = f"书籍_{isbn}"
                    print(f"没有找到标题，使用ISBN作为文件名: {clean_title}")
                else:
                    # 使用文件名
                    clean_title = json_filename
                    print(f"没有找到标题或ISBN，使用原文件名: {json_filename}")
            
            # 限制文件名长度，避免过长
            if len(clean_title) > 100:
                clean_title = clean_title[:100]
            
            output_dir = os.path.dirname(json_file).replace('json', 'markdown')
            output_file = os.path.join(output_dir, f"{clean_title}.md")
        
        # 使用共用的转换函数生成Markdown内容
        md_content = convert_to_markdown(book_data)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 写入Markdown文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"成功将 {json_file} 转换为 Markdown 格式: {output_file}")
        return output_file
    
    except Exception as e:
        print(f"转换过程中发生错误: {str(e)}", file=sys.stderr)
        return None

# 为了兼容性，创建一个别名函数
def convert_to_markdown(book_data):
    """
    将书籍数据转换为Markdown格式，先显示封面，然后是基本信息
    
    Args:
        book_data (dict): The book data dictionary
    
    Returns:
        str: Markdown formatted content
    """
    # 生成Markdown内容
    md_content = []
    
    # 封装一个处理YAML值中的换行符的函数
    def clean_yaml_value(value):
        """处理YAML值中的换行符和特殊字符，避免破坏YAML格式"""
        if not value:
            return ""
        
        if isinstance(value, str):
            # 替换换行符为空格
            value = value.replace('\n', ' ')
            
            # 特殊处理：对于作者字段，始终使用引号包裹，因为作者名称经常包含可能破坏YAML格式的字符
            # 同时检查其他可能导致YAML解析问题的字符
            if ':' in value or '[' in value or ']' in value or '{' in value or '}' in value or \
               '#' in value or '&' in value or '*' in value or '!' in value or '|' in value or \
               '>' in value or "'" in value or '"' in value or '%' in value or '@' in value or \
               '`' in value or ',' in value or '-' in value or '?' in value:
                # 如果包含双引号，先将其转义
                value = value.replace('"', '\\"')
                return f'"{value}"'
            return value
        return value
    
    # 添加YAML frontmatter
    md_content.append("---")
    
    # 书名
    title = book_data.get('标题') or book_data.get('书名') or book_data.get('title', '')
    md_content.append(f"书名: {clean_yaml_value(title)}")
    
    # 主题 (暂时为空)
    md_content.append("主题: ")
    
    # 作者
    author = book_data.get('作者') or book_data.get('author', '')
    # 强制对作者使用引号包裹
    if author:
        author_value = clean_yaml_value(author)
        # 确保作者始终使用引号包裹
        if not (author_value.startswith('"') and author_value.endswith('"')):
            # 转义已存在的双引号
            author_value = author.replace('"', '\\"')
            author_value = f'"{author_value}"'
        md_content.append(f"作者: {author_value}")
    else:
        md_content.append("作者: ")
    
    # 出版社
    publisher = book_data.get('出版社') or book_data.get('publisher', '')
    if not publisher:
        publisher = book_data.get('publisherName', '') or book_data.get('publish', '')
    md_content.append(f"出版社: {clean_yaml_value(publisher)}")
    
    # 出版时间
    pub_date = book_data.get('出版时间') or book_data.get('publication_date', '')
    if not pub_date:
        pub_date = book_data.get('publicationDate', '') or book_data.get('publishDate', '')
    md_content.append(f"出版时间: {clean_yaml_value(pub_date)}")
    
    # 书本页面
    book_url = book_data.get('书本页面') or book_data.get('URL') or book_data.get('book_url', '') or book_data.get('url', '')
    md_content.append(f"书本页面: {clean_yaml_value(book_url)}")
    
    # 作者页面
    author_url = book_data.get('作者页面') or book_data.get('author_url', '')
    md_content.append(f"作者页面: {clean_yaml_value(author_url)}")
    
    # 评分
    rating_text = ""
    amazon_rating = book_data.get('评分') or book_data.get('rating', '') or book_data.get('amazon_rating', '')
    amazon_count = book_data.get('amazon_rating_count', '')
    goodreads_rating = book_data.get('goodreads_rating', '')
    goodreads_count = book_data.get('goodreads_rating_count', '')
    
    if amazon_rating:
        rating_text = amazon_rating
        if amazon_count:
            rating_text += f" ({amazon_count})"
        if goodreads_rating:
            rating_text += f", Goodreads: {goodreads_rating}"
            if goodreads_count:
                rating_text += f" ({goodreads_count})"
    elif goodreads_rating:
        rating_text = f"Goodreads: {goodreads_rating}"
        if goodreads_count:
            rating_text += f" ({goodreads_count})"
    
    md_content.append(f"评分: {clean_yaml_value(rating_text)}")
    
    # 作者简介
    author_bio = book_data.get('作者简介') or book_data.get('author_bio', '')
    md_content.append(f"作者简介: {clean_yaml_value(author_bio)}")
    
    # 内容简介
    book_description = book_data.get('内容简介') or book_data.get('description', '')
    md_content.append(f"内容简介: {clean_yaml_value(book_description)}")
    
    # 封面
    cover_url = book_data.get('封面') or book_data.get('cover_image_url') or book_data.get('cover_image') or book_data.get('imageUrl', '')
    if cover_url and not cover_url.startswith(('http://', 'https://')):
        if cover_url.startswith('//'):
            cover_url = 'https:' + cover_url
    md_content.append(f"封面: {clean_yaml_value(cover_url)}")
    
    # 备注
    md_content.append("备注: ")
    
    # 结束YAML frontmatter
    md_content.append("---")
    md_content.append("")
    
    # 书名作为标题
    md_content.append(f"# {title}")
    md_content.append("")
    
    # 添加封面图片（如果有）- 直接使用图片链接，不添加前缀文字
    if cover_url:
        md_content.append(f"![]({cover_url})")
        md_content.append("")
    
    # 基本信息表格
    md_content.append("## 基本信息")
    md_content.append("")
    md_content.append("| 项目 | 内容 |")
    md_content.append("| --- | --- |")
    
    # 封装一个处理表格值中换行符的函数，用于所有表格字段
    def clean_table_value(value):
        """处理表格值中的换行符，避免破坏表格格式"""
        if isinstance(value, str):
            return value.replace('\n', ' ')
        return value
    
    # 书本页面
    if book_url:
        book_url = clean_table_value(book_url)
        md_content.append(f"| 书本页面 | {book_url} |")
    
    # 作者信息
    if author:
        author = clean_table_value(author)
        md_content.append(f"| 作者 | {author} |")
    
    # 作者页面
    if author_url:
        author_url = clean_table_value(author_url)
        md_content.append(f"| 作者页面 | {author_url} |")
    
    # 出版社
    if publisher:
        publisher = clean_table_value(publisher)
        md_content.append(f"| 出版社 | {publisher} |")
        
    # 出版时间
    if pub_date:
        pub_date = clean_table_value(pub_date) 
        md_content.append(f"| 出版时间 | {pub_date} |")
    
    # ISBN - 尝试所有可能的字段名
    isbn = book_data.get('ISBN') or book_data.get('isbn', '')
    if not isbn and 'details' in book_data:
        if isinstance(book_data['details'], dict):
            isbn = book_data['details'].get('isbn', '')
        elif isinstance(book_data['details'], list):
            for detail in book_data['details']:
                if isinstance(detail, dict) and 'name' in detail and detail['name'].lower() == 'isbn':
                    isbn = detail.get('value', '')
                    break
    if isbn:
        isbn = clean_table_value(isbn)
        md_content.append(f"| ISBN | {isbn} |")
        
    # 作者简介
    if author_bio:
        author_bio = clean_table_value(author_bio)
        md_content.append(f"| 作者简介 | {author_bio} |")
    
    # 内容简介
    if book_description:
        book_description = clean_table_value(book_description)
        md_content.append(f"| 内容简介 | {book_description} |")
    
    # 评分
    if rating_text:
        rating_text = clean_table_value(rating_text)
        md_content.append(f"| 评分 | {rating_text} |")
    
    md_content.append("")
    
    # 关联图书
    related_books = book_data.get('相关图书') or book_data.get('关联图书') or book_data.get('related_books', [])
    if related_books:
        md_content.append("## 关联图书")
        md_content.append("")
        
        if isinstance(related_books, list):
            for book in related_books:
                if isinstance(book, dict) and 'title' in book and 'url' in book:
                    # 处理dict格式的书籍
                    md_content.append(f"- [{book['title']}]({book['url']})")
                elif isinstance(book, str):
                    # 处理字符串格式的书籍
                    if " - http" in book:
                        # 匹配"书名 - URL"的格式
                        parts = book.split(" - ", 1)
                        title = parts[0].strip()
                        url = parts[1].strip()
                        md_content.append(f"- [{title}]({url})")
                    else:
                        # 直接添加
                        md_content.append(f"- {book}")
        elif isinstance(related_books, str):
            # 处理字符串格式的关联图书(按行分割)
            for line in related_books.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                if " - http" in line:
                    parts = line.split(" - ", 1)
                    title = parts[0].strip()
                    url = parts[1].strip()
                    md_content.append(f"- [{title}]({url})")
                else:
                    md_content.append(f"- {line}")
        
        md_content.append("")
    
    # 读者评论
    reviews = book_data.get('评论') or book_data.get('读者评论') or book_data.get('reviews', [])
    if reviews:
        md_content.append("## 读者评论")
        md_content.append("")
        
        if isinstance(reviews, list):
            for i, review in enumerate(reviews, 1):
                md_content.append(f"### 评论 {i}")
                md_content.append("")
                
                if isinstance(review, dict):
                    # 评论者
                    reviewer_name = review.get('reviewer_name', '')
                    if reviewer_name:
                        md_content.append(f"- **评论者**: {reviewer_name}")
                    
                    # 评分
                    rating = review.get('rating', '')
                    if rating:
                        md_content.append(f"- **评分**: {rating}")
                    
                    # 标题
                    title = review.get('title', '')
                    if title:
                        md_content.append(f"- **标题**: {title}")
                    
                    # 日期
                    date = review.get('date', '')
                    if date:
                        md_content.append(f"- **日期**: {date}")
                    
                    # 内容
                    content = review.get('content', '')
                    if content:
                        md_content.append(f"- **内容**: {content}")
                elif isinstance(review, str):
                    md_content.append(review)
                
                md_content.append("")
        elif isinstance(reviews, str):
            # 按段落分割评论
            paragraphs = reviews.split('\n\n')
            for paragraph in paragraphs:
                if paragraph.strip():
                    md_content.append(paragraph.strip())
                    md_content.append("")
    
    # 返回Markdown内容
    return '\n'.join(md_content)

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
