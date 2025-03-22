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
import re

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

# 添加TheBrain导入专用日志
brain_logger = logging.getLogger("TheBrainImport")
brain_handler = logging.FileHandler("thebrain_import.log")
brain_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
brain_logger.setLevel(logging.INFO)
brain_logger.addHandler(brain_handler)
brain_logger.addHandler(logging.StreamHandler())

# 导入自定义模块
try:
    from amazon_feishu_extractor import extract_from_file, convert_to_feishu_format
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

def process_book(html_file, output_dir, feishu_webhook_url=None, region="us", url=None, domain=None):
    """Process Amazon book HTML and generate output files."""
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建子目录
    json_dir = os.path.join(output_dir, "json")
    markdown_dir = os.path.join(output_dir, "markdown")
    html_dir = os.path.join(output_dir, "html")
    
    for directory in [json_dir, markdown_dir, html_dir]:
        os.makedirs(directory, exist_ok=True)
    
    # 提取文件名（不含扩展名）作为书籍标识
    book_identifier = os.path.splitext(os.path.basename(html_file))[0]
    
    # 解析HTML
    logger.info(f"Reading HTML file: {html_file}")
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 从域名判断区域，传递domain参数
    if domain:
        logger.info(f"Using domain from frontend: {domain}")
    else:
        # 尝试从URL或文件名判断区域
        if url and "amazon.co.uk" in url:
            domain = "amazon.co.uk"
        elif url and "amazon.co.jp" in url:
            domain = "amazon.co.jp"
        elif "co.uk" in html_file:
            domain = "amazon.co.uk"
        elif "co.jp" in html_file:
            domain = "amazon.co.jp"
        
        if domain:
            logger.info(f"Detected domain from file/URL: {domain}")
    
    # 提取数据，传递domain参数
    logger.info("Extracting book data...")
    book_data = extract_from_file(html_file, region=region, domain=domain)
    
    # 确保book_data不为None
    if book_data is None:
        logger.error("Failed to extract book data from file")
        return False
    
    if url and url.strip():
        # 如果提供了原始URL，添加到数据中
        book_data['url'] = url.strip()
        book_data['书本页面'] = url.strip()
    
    # 将数据保存为JSON
    json_file = os.path.join(json_dir, f"{book_identifier}.json")
    logger.info(f"Saving JSON data to: {json_file}")
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(book_data, f, ensure_ascii=False, indent=2)
    
    # 将JSON转换为Markdown
    markdown_content = convert_to_markdown(book_data)
    
    # 为Markdown文件生成文件名 - 只保留书名
    title = book_data.get('标题') or book_data.get('书名') or book_data.get('title', '')
    if title:
        # 限制文件名长度
        if len(title) > 100:
            title = title[:100]
        
        markdown_file = os.path.join(markdown_dir, f"{title}.md")
        logger.info(f"Using book title as filename: {title}")
    else:
        # 如果找不到标题，尝试使用ISBN
        isbn = book_data.get('ISBN', book_data.get('isbn', ''))
        if isbn:
            markdown_file = os.path.join(markdown_dir, f"书籍_{isbn}.md")
            logger.info(f"No title found, using ISBN as filename: {isbn}")
        else:
            # 如果没有标题和ISBN，使用原始文件名
            markdown_file = os.path.join(markdown_dir, f"{book_identifier}.md")
            logger.info(f"No title or ISBN found, using original filename: {book_identifier}")
    
    logger.info(f"Saving Markdown to: {markdown_file}")
    
    with open(markdown_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    # 如果提供了Feishu webhook URL，则发送数据到Feishu
    if feishu_webhook_url:
        logger.info("Preparing data for Feishu...")
        try:
            # 将数据转换为Feishu格式
            feishu_data = convert_to_feishu_format(book_data)
            
            # 确保feishu_data是正确的格式
            if not isinstance(feishu_data, dict):
                logger.error(f"Invalid Feishu data format: expected dict, got {type(feishu_data)}")
                logger.debug(f"Feishu data content: {feishu_data}")
                return json_file, markdown_file
            
            # 检查必要的字段是否存在
            expected_keys = ["书名", "书本页面", "作者", "内容简介"]
            missing_keys = [k for k in expected_keys if k not in feishu_data or not feishu_data[k]]
            
            if missing_keys:
                logger.warning(f"Missing important Feishu data fields: {', '.join(missing_keys)}")
                logger.debug(f"Feishu data keys: {feishu_data.keys()}")
            
            # 打印feishu_data内容，用于调试
            logger.debug(f"Feishu data: {json.dumps(feishu_data, ensure_ascii=False, indent=2)}")
            
            logger.info("Sending data to Feishu...")
            # 直接使用import的send_to_feishu函数
            success = send_to_feishu(feishu_data, feishu_webhook_url)
            
            if success:
                logger.info("Successfully sent data to Feishu")
            else:
                logger.error("Failed to send data to Feishu")
        except Exception as e:
            logger.error(f"Error sending data to Feishu: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    else:
        logger.warning("No Feishu webhook URL provided, skipping sending data to Feishu")
    
    # 添加:自动导入数据到TheBrain
    try:
        # 检查父目录下是否存在auto_brain_importer.py
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        auto_importer_path = os.path.join(parent_dir, "auto_brain_importer.py")
        
        if os.path.exists(auto_importer_path):
            # 导入auto_brain_importer模块
            sys.path.insert(0, parent_dir)
            try:
                from auto_brain_importer import auto_import_book
                from brain_importer import process_markdown_content
                
                brain_logger.info(f"开始自动导入Amazon图书到TheBrain: {title}")
                brain_logger.info(f"JSON文件路径: {json_file}")
                
                # 使用process_markdown_content处理Markdown内容，确保移除标题
                # 自动导入时会再次调用此函数，这里只是确保日志一致性
                processed_content = process_markdown_content(markdown_content)
                brain_logger.info(f"已处理Markdown内容，移除了YAML frontmatter和标题")
                
                # 调用导入函数
                import_result = auto_import_book(book_data)
                
                if import_result.get("success"):
                    brain_logger.info(f"成功将书籍导入到TheBrain: {title}")
                    brain_logger.info(f"Thought ID: {import_result.get('thought_id')}")
                else:
                    brain_logger.error(f"导入到TheBrain失败: {import_result.get('message')}")
            except ImportError as e:
                brain_logger.error(f"导入auto_brain_importer模块失败: {str(e)}")
        else:
            brain_logger.warning(f"未找到auto_brain_importer.py，跳过导入到TheBrain。路径: {auto_importer_path}")
    except Exception as e:
        brain_logger.error(f"导入到TheBrain时出错: {str(e)}")
        import traceback
        brain_logger.error(traceback.format_exc())
    
    return json_file, markdown_file

def main():
    """主函数"""
    # 清理pycache目录，防止干扰
    import shutil
    try:
        shutil.rmtree('__pycache__', ignore_errors=True)
    except:
        pass
    
    parser = argparse.ArgumentParser(description="处理亚马逊图书HTML文件")
    parser.add_argument("--html", required=True, help="HTML文件路径")
    parser.add_argument("--output-dir", required=True, help="输出目录")
    parser.add_argument("--feishu-webhook", help="飞书Webhook URL")
    parser.add_argument("--region", default="us", help="亚马逊区域代码 (us, uk, jp)")
    parser.add_argument("--url", help="原始URL")
    parser.add_argument("--domain", help="亚马逊域名 (amazon.com, amazon.co.uk, amazon.co.jp)")
    
    args = parser.parse_args()
    
    success = process_book(
        args.html, 
        args.output_dir, 
        args.feishu_webhook,
        region=args.region,
        url=args.url,
        domain=args.domain
    )
    
    if success:
        print("处理成功!")
        return 0
    else:
        print("处理失败，请查看日志获取详细信息。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
