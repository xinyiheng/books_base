#!/usr/bin/env python3
"""
Amazon Book Processor
处理下载的HTML文件，生成JSON和Markdown文件，并发送数据到飞书
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("amazon_book_processor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AmazonBookProcessor")

# 导入自定义模块
try:
    from amazon_feishu_extractor import extract_from_file
    from feishu_webhook import send_to_feishu
    from json_to_markdown import convert_to_markdown
except ImportError as e:
    logger.error(f"导入模块失败: {str(e)}")
    logger.error("请确保所有必要的Python脚本都在同一目录下")
    sys.exit(1)

def ensure_directory_exists(directory):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
            logger.info(f"创建目录: {directory}")
        except Exception as e:
            logger.error(f"创建目录失败: {directory}, 错误: {str(e)}")
            return False
    return True

def process_book(html_file, output_dir, feishu_webhook_url=None):
    """
    处理亚马逊图书HTML文件
    
    参数:
        html_file (str): HTML文件路径
        output_dir (str): 输出目录
        feishu_webhook_url (str, optional): 飞书Webhook URL
    
    返回:
        bool: 处理是否成功
    """
    try:
        # 确保输出目录存在
        html_dir = os.path.join(output_dir, "html")
        json_dir = os.path.join(output_dir, "json")
        markdown_dir = os.path.join(output_dir, "markdown")
        
        for directory in [html_dir, json_dir, markdown_dir]:
            if not ensure_directory_exists(directory):
                return False
        
        # 获取文件名（不含扩展名）
        file_basename = os.path.basename(html_file)
        file_name = os.path.splitext(file_basename)[0]
        
        # 如果HTML文件不在html目录中，复制一份到html目录
        if not html_file.startswith(html_dir):
            import shutil
            html_dest = os.path.join(html_dir, file_basename)
            shutil.copy2(html_file, html_dest)
            logger.info(f"复制HTML文件到: {html_dest}")
            html_file = html_dest
        
        # 提取图书信息
        logger.info(f"从HTML文件提取图书信息: {html_file}")
        book_info = extract_from_file(html_file)
        
        if not book_info:
            logger.error("提取图书信息失败")
            return False
        
        # 从文件名中提取ASIN和书名（如果存在）
        asin = None
        book_title = None
        
        # 尝试从文件名中提取ASIN和书名
        import re
        asin_match = re.search(r'amazon_book_([A-Z0-9]{10})_', file_name)
        if asin_match:
            asin = asin_match.group(1)
            
            # 尝试提取书名（如果文件名中包含）
            title_match = re.search(r'amazon_book_[A-Z0-9]{10}_(.+?)(?:_\d{4}-\d{2}-\d{2}T|$)', file_name)
            if title_match:
                book_title = title_match.group(1)
        
        # 如果文件名中没有提取到书名，使用提取的图书信息中的标题
        if not book_title and 'title' in book_info and book_info['title']:
            book_title = book_info['title']
        
        # 清理书名，移除特殊字符，限制长度
        if book_title:
            # 仅限制长度，不替换特殊字符
            if len(book_title) > 100:
                book_title = book_title[:100]
        
        # 为JSON和Markdown文件创建更友好的文件名
        json_filename = file_name  # 保持原始文件名（包含时间戳）
        
        # 为Markdown文件创建只包含书名的文件名
        if book_title:
            markdown_filename = book_title
        elif asin:
            # 如果没有书名但有ASIN，使用ASIN
            markdown_filename = f"amazon_book_{asin}"
        else:
            # 如果无法提取ASIN和书名，使用原始文件名
            markdown_filename = file_name
        
        # 保存JSON文件
        json_file = os.path.join(json_dir, f"{json_filename}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(book_info, f, ensure_ascii=False, indent=2)
        logger.info(f"保存JSON文件: {json_file}")
        
        # 转换为Markdown并保存（使用只包含书名的文件名）
        markdown_file = os.path.join(markdown_dir, f"{markdown_filename}.md")
        markdown_content = convert_to_markdown(book_info)
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        logger.info(f"保存Markdown文件: {markdown_file}")
        
        # 发送到飞书（如果提供了webhook URL）
        if feishu_webhook_url:
            logger.info("发送数据到飞书...")
            success = send_to_feishu(feishu_webhook_url, book_info)
            if success:
                logger.info("成功发送数据到飞书")
            else:
                logger.warning("发送数据到飞书失败")
        
        logger.info("处理完成!")
        return True
    
    except Exception as e:
        logger.error(f"处理图书时发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="处理亚马逊图书HTML文件")
    parser.add_argument("--html", required=True, help="HTML文件路径")
    parser.add_argument("--output-dir", required=True, help="输出目录")
    parser.add_argument("--feishu-webhook", help="飞书Webhook URL")
    
    args = parser.parse_args()
    
    success = process_book(args.html, args.output_dir, args.feishu_webhook)
    
    if success:
        print("处理成功!")
        return 0
    else:
        print("处理失败，请查看日志获取详细信息。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
