#!/usr/bin/env python3
"""
The Brain Book Importer
将书籍JSON数据导入到The Brain作为Thought和Note
"""

import os
import sys
import json
import argparse
import requests
import logging
import re
import glob
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("brain_importer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BrainImporter")

class BrainImporter:
    def __init__(self, brain_id, api_key):
        """初始化Brain导入器"""
        self.brain_id = brain_id
        self.api_key = api_key
        # 使用正确的API地址
        self.api_base_url = "https://api.bra.in"
        # 设置正确的请求头
        self.headers = {
            "Accept": "*/*",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json-patch+json"
        }
        logger.info(f"初始化Brain导入器，Brain ID: {self.brain_id}")
        logger.info(f"使用API Base URL: {self.api_base_url}")
    
    def create_thought(self, name, label=None, source_thought_id=None, relation=1, kind=1, ac_type=0):
        """创建一个新的Thought"""
        # 根据官方文档使用正确的API路径
        url = f"{self.api_base_url}/thoughts/{self.brain_id}"
        
        # 准备基本payload
        payload = {
            "name": name,
            "kind": kind,
            "acType": ac_type
        }
        
        if label:
            payload["label"] = label
            
        # 如果提供了源思想ID，则添加关系信息
        if source_thought_id:
            payload["sourceThoughtId"] = source_thought_id
            payload["relation"] = relation
        
        logger.info(f"创建Thought: {name}")
        logger.debug(f"API URL: {url}")
        logger.debug(f"Payload: {payload}")
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=15)
            
            if response.status_code in [200, 201]:
                thought_data = response.json()
                thought_id = thought_data.get('id')
                if thought_id:
                    logger.info(f"成功创建Thought，ID: {thought_id}")
                    return thought_data
                else:
                    logger.warning(f"返回数据中没有ID: {thought_data}")
            else:
                status = response.status_code
                error_text = response.text[:100] if response.text else ""
                logger.error(f"创建Thought失败: {status} - {error_text}")
                
        except Exception as e:
            logger.error(f"创建Thought时发生错误: {str(e)}")
        
        return None
    
    def update_note(self, thought_id, markdown_content):
        """更新Thought的Note内容"""
        # 根据官方文档使用正确的API路径
        url = f"{self.api_base_url}/notes/{self.brain_id}/{thought_id}/append"
        
        # 准备payload - 使用markdown字段而不是content
        payload = {
            "markdown": markdown_content
        }
        
        logger.info(f"更新Thought ID {thought_id}的Note")
        logger.debug(f"API URL: {url}")
        logger.debug(f"Payload长度: {len(markdown_content)} 字符")
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201, 204]:
                logger.info(f"成功更新Note")
                return True
            else:
                status = response.status_code
                error_text = response.text[:100] if response.text else ""
                logger.error(f"更新Note失败: {status} - {error_text}")
                
        except Exception as e:
            logger.error(f"更新Note时发生错误: {str(e)}")
        
        return False

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

def process_markdown_content(md_content):
    """处理Markdown内容，移除开头的属性信息和书名标题，但保留封面图片，只保留正文内容"""
    if not md_content:
        return ""
    
    # 检查YAML前置元数据部分
    yaml_start = md_content.find('---')
    if yaml_start == 0:
        yaml_end = md_content.find('---', 3)
        if yaml_end > 0:
            # 跳过YAML部分
            content = md_content[yaml_end+3:].strip()
            
            # 只移除第一行的书名（通常是以"# 书名"格式出现），但保留封面图片
            lines = content.split('\n')
            if lines and (lines[0].startswith('# ') or lines[0].startswith('#')):
                # 移除书名标题行，但保留其他内容
                content = '\n'.join(lines[1:]).strip()
                # 如果有空行，也移除
                if content.startswith('\n'):
                    content = content.lstrip('\n')
            
            return content
    
    # 如果没有YAML前置元数据，检查第一行是否是书名标题
    lines = md_content.split('\n')
    if lines and (lines[0].startswith('# ') or lines[0].startswith('#')):
        # 移除书名标题行，但保留其他内容
        content = '\n'.join(lines[1:]).strip()
        # 如果有空行，也移除
        if content.startswith('\n'):
            content = content.lstrip('\n')
        return content
    
    # 如果没有YAML前置元数据和书名标题，直接返回内容
    return md_content

def import_book_to_brain(json_file, brain_id, api_key, source_thought_id=None):
    """将书籍信息导入到The Brain"""
    # 检查文件是否存在
    if not os.path.exists(json_file):
        logger.error(f"JSON文件不存在: {json_file}")
        return False
    
    # 读取JSON文件内容
    with open(json_file, 'r', encoding='utf-8') as f:
        try:
            book_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"JSON文件格式错误: {e}")
            return False
    
    # 提取书名
    book_title = book_data.get('标题') or book_data.get('书名') or book_data.get('title', '')
    if not book_title:
        logger.error(f"无法从JSON中提取书名")
        return False
    
    logger.info(f"处理书籍: {book_title}")
    
    # 生成Markdown内容
    md_content = convert_to_markdown(book_data)
    
    # 处理Markdown内容，移除开头的属性信息
    md_content = process_markdown_content(md_content)
    
    # 初始化Brain导入器
    brain_importer = BrainImporter(brain_id, api_key)
    
    # 创建Thought
    thought_data = brain_importer.create_thought(book_title, source_thought_id=source_thought_id)
    if not thought_data:
        logger.error(f"创建Thought失败，无法继续")
        return False
    
    # 提取Thought ID
    thought_id = thought_data.get('id')
    if not thought_id:
        logger.error(f"无法获取Thought ID，无法继续")
        return False
    
    # 更新Note内容
    success = brain_importer.update_note(thought_id, md_content)
    
    if success:
        logger.info(f"成功将书籍 '{book_title}' 导入到The Brain")
        return True
    else:
        logger.error(f"将书籍导入到The Brain失败")
        return False

def import_directory(directory, brain_id, api_key, source_thought_id=None, pattern="*.json", days=None):
    """从目录导入所有匹配的JSON文件到The Brain"""
    dir_path = Path(directory)
    
    # 检查目录是否存在
    if not dir_path.exists() or not dir_path.is_dir():
        logger.error(f"目录不存在: {directory}")
        return False
    
    # 获取所有匹配的JSON文件
    json_files = list(dir_path.glob(pattern))
    
    # 如果指定了天数，只处理最近N天内的文件
    if days is not None:
        days = int(days)
        import time
        now = time.time()
        filtered_files = []
        for file_path in json_files:
            file_mtime = file_path.stat().st_mtime
            if (now - file_mtime) <= (days * 24 * 60 * 60):
                filtered_files.append(file_path)
        json_files = filtered_files
    
    # 检查是否找到文件
    if not json_files:
        logger.warning(f"没有找到匹配的JSON文件: {pattern}")
        return False
    
    logger.info(f"找到 {len(json_files)} 个JSON文件")
    
    # 处理每个文件
    success_count = 0
    for json_file in json_files:
        if import_book_to_brain(str(json_file), brain_id, api_key, source_thought_id):
            success_count += 1
    
    logger.info(f"成功导入 {success_count}/{len(json_files)} 本书到The Brain")
    return success_count > 0

def process_json_input(input_pattern, brain_id, api_key, source_thought_id=None):
    """处理JSON输入模式，可以是单个文件或包含通配符的模式"""
    # 检查是否是目录+模式
    if os.path.isdir(os.path.dirname(input_pattern)) and ('*' in input_pattern or '?' in input_pattern):
        # 使用glob处理模式
        json_files = glob.glob(input_pattern)
        if not json_files:
            logger.error(f"没有找到匹配的文件: {input_pattern}")
            return False
        
        logger.info(f"找到 {len(json_files)} 个匹配的JSON文件")
        
        # 处理每个文件
        success_count = 0
        for json_file in json_files:
            if import_book_to_brain(json_file, brain_id, api_key, source_thought_id):
                success_count += 1
        
        logger.info(f"成功导入 {success_count}/{len(json_files)} 本书到The Brain")
        return success_count > 0
    
    # 单个文件处理
    elif os.path.isfile(input_pattern):
        return import_book_to_brain(input_pattern, brain_id, api_key, source_thought_id)
    
    # 目录处理
    elif os.path.isdir(input_pattern):
        return import_directory(input_pattern, brain_id, api_key, source_thought_id)
    
    else:
        logger.error(f"无效的输入: {input_pattern} - 既不是文件也不是目录")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="将书籍JSON数据导入到The Brain作为Thought和Note")
    parser.add_argument("--input", "-i", required=True, help="JSON文件路径、目录或通配符模式")
    parser.add_argument("--brain-id", required=True, help="The Brain ID")
    parser.add_argument("--api-key", required=True, help="The Brain API Key")
    parser.add_argument("--source-thought-id", help="源Thought ID，用于创建关联关系")
    parser.add_argument("--days", type=int, help="只处理最近N天的文件")
    
    args = parser.parse_args()
    
    # 处理输入
    success = process_json_input(args.input, args.brain_id, args.api_key, args.source_thought_id)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())