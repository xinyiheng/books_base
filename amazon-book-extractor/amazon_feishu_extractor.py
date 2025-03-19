#!/usr/bin/env python3
"""
Amazon Book Information Extractor for Feishu
This script extracts book information from Amazon product pages and formats it for Feishu
"""

import os
import sys

# 设置Python缓存目录
cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache', 'pycache')
# 确保缓存目录存在
os.makedirs(cache_dir, exist_ok=True)
# 修改Python的缓存目录
sys.pycache_prefix = cache_dir

import re
import json
import argparse
import traceback
import requests
from bs4 import BeautifulSoup
import urllib.parse

# 检查并安装必要的依赖
try:
    import chardet
except ImportError:
    print("Installing chardet library...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "chardet"])
    import chardet
    print("chardet library installed successfully.")

import time
import random
import urllib.parse
from urllib.parse import urljoin
from datetime import datetime  # 添加此导入用于时间戳处理

# Set a user agent to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.google.com/',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
    'Sec-Fetch-User': '?1',
}

# Amazon domain mapping for supported regions
AMAZON_DOMAINS = {
    "com": "https://www.amazon.com", # US
    "co.uk": "https://www.amazon.co.uk", # UK
    "co.jp": "https://www.amazon.co.jp", # Japan
}

def detect_amazon_domain(url):
    """
    Detect Amazon domain from URL
    Returns the base URL for the detected domain
    """
    parsed_url = urllib.parse.urlparse(url)
    domain = parsed_url.netloc
    
    # Extract the domain part (e.g., 'amazon.com', 'amazon.co.uk', etc.)
    amazon_domain = None
    for supported_domain in AMAZON_DOMAINS.keys():
        if f"amazon.{supported_domain}" in domain:
            amazon_domain = supported_domain
            break
    
    if amazon_domain:
        return AMAZON_DOMAINS[amazon_domain]
    
    # Default to US Amazon if domain not recognized
    print(f"Warning: Unrecognized Amazon domain in URL: {url}")
    print(f"Defaulting to Amazon US (amazon.com)")
    return AMAZON_DOMAINS["com"]

def extract_book_info_from_html(html_content, base_url="https://www.amazon.com", file_name=None, domain=None):
    """Extract book information from HTML content"""
    print(f"\n开始从HTML提取图书信息...")
    print(f"使用base_url: {base_url}")
    print(f"文件名: {file_name}")
    print(f"指定域名: {domain}")
    
    # 确定域名和相应的提取函数
    if domain:
        print(f"使用指定域名: {domain}")
    elif "amazon.co.uk" in base_url:
        domain = "amazon.co.uk"
        print(f"从base_url检测到域名: {domain}")
    elif "amazon.co.jp" in base_url:
        domain = "amazon.co.jp"
        print(f"从base_url检测到域名: {domain}")
    else:
        # 默认使用美国亚马逊
        domain = "amazon.com"
        print(f"未检测到特定域名，默认使用: {domain}")
    
    # 根据域名选择合适的提取函数
    if domain == "amazon.co.uk":
        print("使用英国亚马逊提取函数")
        book_info = extract_uk_book_info(html_content, file_name=file_name, base_url=base_url)
    elif domain == "amazon.co.jp":
        print("使用日本亚马逊提取函数")
        book_info = extract_jp_book_info(html_content, file_name=file_name, base_url=base_url)
    else:
        print("使用美国亚马逊提取函数(默认)")
        book_info = extract_us_book_info(html_content, file_name=file_name, base_url=base_url)
    
    # 检查提取结果
    if not book_info:
        print("提取失败，book_info为空")
        return None
    
    # 记录提取到的字段数量
    field_count = len(book_info.keys())
    print(f"成功提取了 {field_count} 个字段的数据")
    
    # 返回提取的数据
    return book_info

def convert_to_feishu_format(original_book_info):
    """Convert book information to Feishu format"""
    # 打印原始数据信息，帮助调试
    print("原始数据字段:")
    for key, value in original_book_info.items():
        if isinstance(value, (list, dict)):
            print(f"  {key}: {type(value)} 类型，包含 {len(value)} 项")
        else:
            value_preview = str(value)[:50] + "..." if value and len(str(value)) > 50 else str(value)
            print(f"  {key}: {value_preview}")
    
    # 检查关键字段是否存在
    critical_fields = ['title', '书名', 'author', '作者', 'description', '内容简介']
    missing_fields = [field for field in critical_fields if field not in original_book_info or not original_book_info.get(field)]
    
    if missing_fields:
        print(f"警告: 原始数据缺少关键字段: {', '.join(missing_fields)}")
        # 检查数据来源，帮助定位问题
        domain = original_book_info.get('domain', '')
        region = original_book_info.get('region', '')
        if domain:
            print(f"数据来源域名: {domain}")
        if region:
            print(f"数据来源区域: {region}")
    
    # 创建飞书卡片格式
    feishu_data = {
        "标题": original_book_info.get('title', original_book_info.get('书名', '')),
        "书名": original_book_info.get('title', original_book_info.get('书名', '')),
        "作者": original_book_info.get('author', original_book_info.get('作者', '')),
        "作者页面": original_book_info.get('author_url', original_book_info.get('作者页面', '')),
        "出版社": original_book_info.get('publisher', original_book_info.get('出版社', '')),
        "出版时间": original_book_info.get('publication_date', original_book_info.get('出版时间', '')),
        "ISBN": original_book_info.get('isbn', original_book_info.get('ISBN', '')),
        "封面": original_book_info.get('cover_image_url', original_book_info.get('封面', original_book_info.get('cover_image', ''))),
        "内容简介": original_book_info.get('description', original_book_info.get('内容简介', '')),
        "作者简介": original_book_info.get('author_bio', original_book_info.get('作者简介', '')),
        "评分": '',
        "书本页面": original_book_info.get('book_url', original_book_info.get('书本页面', original_book_info.get('url', ''))),
    }
    
    # 保留关联图书的原始数据结构，让feishu_webhook.py处理格式转换
    # 使用"关联图书"作为统一字段名
    related_books = original_book_info.get('related_books', original_book_info.get('关联图书', []))
    if related_books:
        feishu_data["关联图书"] = related_books
    else:
        feishu_data["关联图书"] = []
    
    # 保留评论的原始数据结构，让feishu_webhook.py处理格式转换
    # 使用"读者评论"作为统一字段名
    reviews = original_book_info.get('reviews', original_book_info.get('读者评论', []))
    if reviews:
        feishu_data["读者评论"] = reviews
    else:
        feishu_data["读者评论"] = []
    
    # 添加亚马逊评分和Goodreads评分
    amazon_rating = original_book_info.get('amazon_rating', '')
    amazon_rating_count = original_book_info.get('amazon_rating_count', '')
    goodreads_rating = original_book_info.get('goodreads_rating', '')
    goodreads_rating_count = original_book_info.get('goodreads_rating_count', '')
    
    ratings = []
    if amazon_rating:
        if amazon_rating_count:
            ratings.append(f"Amazon: {amazon_rating} ({amazon_rating_count})")
        else:
            ratings.append(f"Amazon: {amazon_rating}")
    
    if goodreads_rating:
        if goodreads_rating_count:
            ratings.append(f"Goodreads: {goodreads_rating} ({goodreads_rating_count})")
        else:
            ratings.append(f"Goodreads: {goodreads_rating}")
    
    feishu_data["评分"] = " | ".join(ratings) if ratings else ""
    
    # 确保 ISBN 信息正确提取
    if 'ISBN' not in feishu_data or not feishu_data['ISBN']:
        # 尝试从其他可能的来源提取
        for isbn_field in ['ISBN', 'isbn', 'isbn10', 'isbn13']:
            if isbn_field in original_book_info and original_book_info[isbn_field]:
                feishu_data['ISBN'] = original_book_info[isbn_field]
                print(f"从字段 '{isbn_field}' 提取到ISBN: {feishu_data['ISBN']}")
                break
    
    # 检查转换后数据的完整性
    empty_fields = [key for key, value in feishu_data.items() 
                   if key not in ["关联图书", "读者评论"] and not value]
    
    if empty_fields:
        print(f"警告: 转换后数据中以下字段为空: {', '.join(empty_fields)}")
    
    # 打印转换后的数据结构，用于调试
    print("\n转换后的飞书数据结构:")
    for key in feishu_data:
        if key in ["关联图书", "读者评论"]:
            print(f"{key}: 包含 {len(feishu_data[key])} 项")
        else:
            value_preview = str(feishu_data[key])[:50] + "..." if len(str(feishu_data[key])) > 50 else str(feishu_data[key])
            print(f"{key}: {value_preview}")
    
    return feishu_data

def extract_from_url(url, domain=None):
    """
    Extract book information from an Amazon product URL
    """
    try:
        # 优先使用前端提供的domain参数
        if domain:
            print(f"使用前端提供的域名: {domain}")
            # 根据domain设置base_url
            if "amazon.co.uk" in domain:
                base_url = "https://www.amazon.co.uk"
            elif "amazon.co.jp" in domain:
                base_url = "https://www.amazon.co.jp"
            else:
                base_url = "https://www.amazon.com"
        else:
            # 如果没有提供domain，从URL检测
            base_url = detect_amazon_domain(url)
        
        print(f"使用base_url: {base_url}")
        
        # 发送请求获取页面内容
        print(f"发送请求到 {url}...")
        time.sleep(random.uniform(1, 3))  # 添加随机延迟
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        # 检查请求是否成功
        if response.status_code != 200:
            print(f"错误: 收到状态码 {response.status_code}")
            return {'error': f'获取页面失败: 状态码 {response.status_code}'}
        
        # 将HTML内容保存到文件用于调试
        with open('amazon_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"已保存HTML内容到 amazon_page.html")
        
        # 从HTML内容提取图书信息，传递domain参数
        return convert_to_feishu_format(extract_book_info_from_html(response.text, domain=domain))
    
    except Exception as e:
        print(f"提取图书信息时出错: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return {'error': f'提取图书信息失败: {str(e)}'}

def extract_uk_book_info(html_content, file_name=None, base_url=None):
    """Extract book information from Amazon UK HTML content"""
    from urllib.parse import urljoin
    soup = BeautifulSoup(html_content, 'html.parser')
    book_info = {}
    
    # Optional ISBN override from filename
    url_isbn_override = None
    if file_name:
        # Try to extract ISBN from filename or provided URL - improved regex patterns
        # ISBN-10 is 10 digits, or 9 digits followed by 'X'
        dp_match = re.search(r'dp/([0-9]{9}[0-9X])\b', file_name)
        if dp_match:
            url_isbn_override = dp_match.group(1)
        elif re.search(r'dp/([0-9]{9}[0-9X])/\b', file_name):
            url_isbn_override = re.search(r'dp/([0-9]{9}[0-9X])/\b', file_name).group(1)
        else:
            # Stricter ISBN-10 pattern - must be 10 digits or 9 digits + X
            isbn10_match = re.search(r'\b([0-9]{9}[0-9X])\b', file_name)
            if isbn10_match:
                url_isbn_override = isbn10_match.group(1)
            else:
                # ISBN-13 is always 13 digits
                isbn13_match = re.search(r'\b([0-9]{13})\b', file_name)
                if isbn13_match:
                    isbn13 = isbn13_match.group(1)
                    # Note: ISBN-10 is not just the last 10 digits of ISBN-13
                    # For now, we'll use the ISBN-13 value directly
                    url_isbn_override = isbn13
    
    # Extract book title
    title_element = soup.select_one('#productTitle')
    if title_element:
        book_info['书名'] = title_element.text.strip()
    
    # Extract author
    author_element = soup.select_one('#bylineInfo .author a')
    if author_element:
        book_info['作者'] = author_element.text.strip()
        author_href = author_element.get('href')
        if author_href:
            if author_href.startswith('http'):
                # 确保链接使用正确的域名
                if 'amazon.com' in author_href and not 'amazon.co.uk' in author_href:
                    author_href = author_href.replace('amazon.com', 'amazon.co.uk')
                book_info['作者页面'] = author_href
            else:
                book_info['作者页面'] = "https://www.amazon.co.uk" + author_href
        else:
            book_info['作者页面'] = ""
    
    # Extract cover image URL
    cover_element = soup.select_one('#imgTagWrapperId img')
    if cover_element:
        if cover_element.get('data-old-hires'):
            book_info['封面'] = cover_element.get('data-old-hires')
        elif cover_element.get('src'):
            book_info['封面'] = cover_element.get('src')
    
    # Extract author bio
    author_bio_element = soup.select_one('._about-the-author-card_style_cardContentDiv__FXLPd')
    if author_bio_element:
        paragraphs = author_bio_element.find_all('p')
        if paragraphs:
            # Join with spaces instead of newlines to avoid MD table issues
            book_info['作者简介'] = ' '.join([p.text.strip() for p in paragraphs])
    
    # Extract book description
    description_element = soup.select_one('#bookDescription_feature_div .a-expander-content')
    if description_element:
        book_info['内容简介'] = description_element.text.strip()
    else:
        description_element = soup.select_one('#productDescription')
        if description_element:
            book_info['内容简介'] = description_element.text.strip()
    
    # Extract ISBN-10 and ISBN-13 - Prioritize ISBN-10 for URL creation
    isbn10 = None
    isbn13 = None
    
    # First try to extract ISBN-10
    isbn10_element = soup.select_one('#rpi-attribute-book_details-isbn10 .rpi-attribute-value, tr:has(th:contains("ISBN-10")) td')
    if isbn10_element:
        isbn10_text = isbn10_element.text.strip().replace('-', '')
        # Validate ISBN-10 format (10 digits or 9 digits + X)
        if re.match(r'^[0-9]{9}[0-9X]$', isbn10_text):
            isbn10 = isbn10_text
            book_info['ISBN'] = isbn10_element.text.strip()
    
    # Then try ISBN-13 if ISBN-10 was not found
    if not isbn10:
        isbn13_element = soup.select_one('#rpi-attribute-book_details-isbn13 .rpi-attribute-value, tr:has(th:contains("ISBN-13")) td')
        if isbn13_element:
            isbn13_text = isbn13_element.text.strip().replace('-', '')
            # Validate ISBN-13 format (always 13 digits)
            if re.match(r'^[0-9]{13}$', isbn13_text):
                isbn13 = isbn13_text
                if 'ISBN' not in book_info:
                    book_info['ISBN'] = isbn13_element.text.strip()
    
    # Try to find ISBN from alternative locations if not found above
    if not isbn10 and not isbn13:
        # Try detail bullets
        detail_elements = soup.select('#detailBullets_feature_div li, #detailBulletsWrapper_feature_div .a-list-item')
        for detail in detail_elements:
            detail_text = detail.text.lower()
            if 'isbn-10' in detail_text:
                isbn_match = re.search(r'isbn-10\s*:?\s*([0-9]{9}[0-9X])', detail_text, re.IGNORECASE)
                if isbn_match:
                    isbn10 = isbn_match.group(1)
                    if 'ISBN' not in book_info:
                        book_info['ISBN'] = isbn10
            elif 'isbn-13' in detail_text and not isbn13:
                isbn_match = re.search(r'isbn-13\s*:?\s*([0-9]{13})', detail_text, re.IGNORECASE)
                if isbn_match:
                    isbn13 = isbn_match.group(1)
                    if 'ISBN' not in book_info:
                        book_info['ISBN'] = isbn13
    
    # If still not found and filename is available, try from filename with stricter validation
    if not isbn10 and not isbn13 and file_name:
        isbn10_match = re.search(r'\b([0-9]{9}[0-9X])\b', file_name)
        if isbn10_match:
            potential_isbn10 = isbn10_match.group(1)
            # Additional validation to ensure it's not capturing something else
            if re.match(r'^[0-9]{9}[0-9X]$', potential_isbn10) and 'books_base' not in potential_isbn10:
                isbn10 = potential_isbn10
                if 'ISBN' not in book_info:
                    book_info['ISBN'] = isbn10
        else:
            isbn13_match = re.search(r'\b([0-9]{13})\b', file_name)
            if isbn13_match:
                potential_isbn13 = isbn13_match.group(1)
                # Additional validation
                if re.match(r'^[0-9]{13}$', potential_isbn13) and 'books_base' not in potential_isbn13:
                    isbn13 = potential_isbn13
                    if 'ISBN' not in book_info:
                        book_info['ISBN'] = isbn13
    
    # Decide which ISBN to use for the URL with better validation
    url_isbn = None
    if url_isbn_override and re.match(r'^[0-9]{9}[0-9X]$|^[0-9]{13}$', url_isbn_override) and 'books_base' not in url_isbn_override:
        url_isbn = url_isbn_override
    elif isbn10:  # Prefer ISBN-10 for URL creation
        url_isbn = isbn10
    elif isbn13:  # Use ISBN-13 if ISBN-10 is not available
        url_isbn = isbn13
    else:
        url_isbn = "1847941834"  # Fallback to a valid example ISBN
    
    # Additional validation to ensure we don't use invalid ISBNs
    if not re.match(r'^[0-9]{9}[0-9X]$|^[0-9]{13}$', url_isbn) or 'books_base' in url_isbn:
        url_isbn = "1847941834"  # Use a known valid ISBN if the detected one is invalid
        print(f"Warning: Invalid ISBN detected, using fallback value")
    
    # Create book URL in the desired format: https://www.amazon.co.uk/dp/{isbn10}
    base_url = "https://www.amazon.co.uk"  # Always use UK domain
    book_url = f"{base_url}/dp/{url_isbn}"
    book_info['书本页面'] = book_url
    
    # Extract publisher and publication date - Keep the existing code
    publisher_found = False
    
    # 尝试多种可能的选择器，按照优先级排序
    publisher_selectors = [
        ('div[data-rpi-attribute-name="book_details-publisher"] .rpi-attribute-value span', 'span selector'),
        ('div[data-rpi-attribute-name="book_details-publisher"] .rpi-attribute-value', 'div selector'),
        ('#rpi-attribute-book_details-publisher .rpi-attribute-value', 'attribute selector'),
        ('tr:has(th:contains("Publisher")) td', 'table selector'),
        ('.a-section:contains("Publisher") + .a-section span', 'section selector'),
        ('#detailBullets_feature_div li:contains("Publisher") span:nth-child(2)', 'detail bullet selector'),
        ('#detailBullets_feature_div li:contains("Publisher") span.a-list-item span:nth-child(2)', 'detail bullet item selector'),
        ('#detailBulletsWrapper_feature_div .a-list-item:contains("Publisher") span:not(:first-child)', 'wrapper detail selector')
    ]
    
    for selector, selector_type in publisher_selectors:
        publisher_element = soup.select_one(selector)
        if publisher_element and publisher_element.text.strip():
            # 确保不是标签文本
            if '出版社' not in publisher_element.text and '発売日' not in publisher_element.text:
                publisher_text = publisher_element.text.strip()
                # 清理日期信息
                publisher_text = re.sub(r'(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{2}/\d{2}/\d{4})', '', publisher_text)
                # 清理括号及其内容
                publisher_text = re.sub(r'\s*\([^)]*\d{4}[^)]*\)', '', publisher_text)
                publisher_text = publisher_text.strip('; :.,')
                
                if publisher_text:
                    book_info['出版社'] = publisher_text
                    print(f"Found publisher from {selector_type}: {book_info['出版社']}")
                    publisher_found = True
                    break
    
    # Publication date extraction - keep existing code
    pub_date_selectors = [
        ('#rpi-attribute-book_details-publication_date .rpi-attribute-value', 'direct selector'),
        ('div[data-rpi-attribute-name="book_details-publication_date"] .rpi-attribute-value', 'attribute selector'),
        ('tr:has(th:contains("Publication date")) td', 'table selector'),
        ('#detailBullets_feature_div li:contains("Publication date") span:nth-child(2)', 'pub date bullet selector')
    ]
    
    pub_date_found = False
    for selector, selector_type in pub_date_selectors:
        pub_date_element = soup.select_one(selector)
        if pub_date_element and pub_date_element.text.strip():
            book_info['出版时间'] = pub_date_element.text.strip()
            print(f"Found publication date from {selector_type}: {book_info['出版时间']}")
            pub_date_found = True
            break
    
    # Extract rating information (similar to JP implementation)
    rating_value = ""
    rating_count = ""

    # Direct rating value extraction
    rating_value_element = soup.select_one('#acrPopover .a-size-base.a-color-base, #acrPopover .a-icon-alt')
    if rating_value_element:
        rating_text = rating_value_element.text.strip()
        # Extract numeric part (e.g., "4.3" or "4.3 out of 5 stars")
        rating_match = re.search(r'([\d\.]+)', rating_text)
        if rating_match:
            rating_value = rating_match.group(1)
    
    # Try alternative methods if the above selector didn't work
    if not rating_value:
        star_element = soup.select_one('span.a-icon-alt')
        if star_element:
            rating_match = re.search(r'([\d\.]+)', star_element.text)
            if rating_match:
                rating_value = rating_match.group(1)

    # Get review count
    rating_count_element = soup.select_one('#acrCustomerReviewText')
    if rating_count_element:
        count_text = rating_count_element.text.strip()
        # Extract numeric part (e.g., "20 ratings")
        count_match = re.search(r'([\d,]+)', count_text)
        if count_match:
            rating_count = count_match.group(1)

    # Set rating information in the book_info
    if rating_value:
        book_info['amazon_rating'] = rating_value
        if rating_count:
            book_info['amazon_rating_count'] = f"{rating_count} ratings"
    
    # Extract related books using same approach as US implementation
    related_books = []
    carousel_elements = soup.select('.a-carousel-card')
    print(f"Found {len(carousel_elements)} carousel elements for related books")
    
    for element in carousel_elements:
        link_element = element.select_one('a[href*="/dp/"]')
        image_element = element.select_one('img')
        title_element = element.select_one('.a-truncate, .p13n-sc-truncate')
        
        if link_element and image_element:
            title_text = ''
            if title_element:
                if title_element.select_one('.a-truncate-full'):
                    title_text = title_element.select_one('.a-truncate-full').text.strip()
                else:
                    title_text = title_element.text.strip()
            elif image_element.get('alt'):
                title_text = image_element.get('alt', '')
            
            if title_text:
                href = link_element.get('href', '')
                # Ensure the URL is complete
                if href.startswith('/'):
                    url = f"https://www.amazon.co.uk{href}"
                else:
                    url = urljoin("https://www.amazon.co.uk", href)
                
                related_book = {
                    "title": title_text,
                    "url": url,
                    "image_url": image_element.get('src', '')
                }
                related_books.append(related_book)
                print(f"Found related book: {related_book['title']}")
    
    # If no related books found, try alternative selectors
    if not related_books:
        # Try other carousel containers
        carousel_containers = soup.select('.a-carousel-container')
        for container in carousel_containers:
            # Check if this is a relevant carousel (look for headings suggesting related books)
            heading = container.find_previous('h2')
            is_relevant = False
            if heading:
                heading_text = heading.text.lower()
                relevant_terms = ['also bought', 'also viewed', 'related to', 'similar items', 'customers also', 'sponsored products']
                for term in relevant_terms:
                    if term in heading_text:
                        is_relevant = True
                        break
            
            if is_relevant or not heading:  # If relevant or we can't determine
                items = container.select('li.a-carousel-card')
                for item in items:
                    link = item.select_one('a[href*="/dp/"]')
                    img = item.select_one('img')
                    if link and img:
                        title = img.get('alt', '')
                        if not title:
                            title_elem = item.select_one('.p13n-sc-truncate')
                            if title_elem:
                                title = title_elem.text.strip()
                        
                        if title:
                            href = link.get('href', '')
                            if href.startswith('/'):
                                url = f"https://www.amazon.co.uk{href}"
                            else:
                                url = urljoin("https://www.amazon.co.uk", href)
                            
                            related_book = {
                                "title": title,
                                "url": url,
                                "image_url": img.get('src', '')
                            }
                            related_books.append(related_book)
                            if len(related_books) >= 10:  # Limit to 10 related books
                                break
            
            if len(related_books) >= 10:
                break
    
    # Add related books to book_info if found
    if related_books:
        book_info['关联图书'] = related_books
    
    # Extract reviews - keep existing code
    reviews = []
    review_elements = soup.select('li[data-hook="review"]')
    
    for review_element in review_elements[:8]:
        review = {}
        
        reviewer_element = review_element.select_one('.a-profile-name')
        if reviewer_element:
            review['reviewer_name'] = reviewer_element.text.strip()
        
        rating_element = review_element.select_one('[data-hook="review-star-rating"]')
        if rating_element:
            rating_text = rating_element.select_one('.a-icon-alt')
            if rating_text:
                rating_match = re.search(r'([\d\.]+) out of', rating_text.text)
                if rating_match:
                    review['rating'] = rating_match.group(1)
        
        title_element = review_element.select_one('a[data-hook="review-title"]')
        if title_element:
            title_text = title_element.text.strip()
            title_text = re.sub(r'^\d+\.\d+ out of \d+ stars\s*', '', title_text)
            review['title'] = title_text.strip()
        
        date_element = review_element.select_one('[data-hook="review-date"]')
        if date_element:
            review['date'] = date_element.text.strip()
        
        text_element = review_element.select_one('[data-hook="review-body"]')
        if text_element:
            content_element = text_element.select_one('[data-hook="review-collapsed"]')
            if content_element:
                review['content'] = content_element.text.strip()
            else:
                review['content'] = text_element.text.strip()
        
        if review:
            reviews.append(review)
    
    if reviews:
        book_info['读者评论'] = reviews
    
    # 添加区域标识
    book_info['region'] = 'uk'
    
    return book_info

def extract_jp_book_info(html_content, file_name=None, base_url=None):
    """Extract book information from Amazon Japan HTML content"""
    from urllib.parse import urljoin
    soup = BeautifulSoup(html_content, 'html.parser')
    book_info = {}
    
    # Optional ISBN override from filename
    url_isbn_override = None
    if file_name:
        dp_match = re.search(r'dp/(\d{10})', file_name)
        if dp_match:
            url_isbn_override = dp_match.group(1)
        elif re.search(r'dp/(\d{10})/', file_name):
            url_isbn_override = re.search(r'dp/(\d{10})/', file_name).group(1)
        else:
            isbn10_match = re.search(r'(?<!\d)(\d{10})(?!\d)', file_name)
            if isbn10_match:
                url_isbn_override = isbn10_match.group(1)
            else:
                isbn13_match = re.search(r'(?<!\d)(\d{13})(?!\d)', file_name)
                if isbn13_match:
                    isbn13 = isbn13_match.group(1)
                    if isbn13.startswith('978') and len(isbn13) > 10:
                        url_isbn_override = isbn13[3:12]
                    else:
                        url_isbn_override = isbn13
    
    # Extract book title
    title_element = soup.select_one('#productTitle')
    if title_element:
        book_info['书名'] = title_element.text.strip()
    
    # 提取作者 - 仅使用 span.author.notFaded a 选择器
    author_found = False
    
    # 首选使用新选择器
    author_element = soup.select_one('span.author.notFaded a')
    if author_element and author_element.text.strip():
        book_info['作者'] = author_element.text.strip()
        
        author_href = author_element.get('href')
        if author_href:
            if author_href.startswith('http'):
                # 确保链接使用正确的域名
                if 'amazon.com' in author_href and not 'amazon.co.jp' in author_href:
                    author_href = author_href.replace('amazon.com', 'amazon.co.jp')
                book_info['作者页面'] = author_href
            else:
                book_info['作者页面'] = "https://www.amazon.co.jp" + author_href
        else:
            book_info['作者页面'] = ""
        
        print(f"Found author using notFaded selector: {book_info['作者']}")
        author_found = True
    
    # 如果没找到作者，使用传统选择器
    if not author_found:
        author_element = soup.select_one('#bylineInfo .author a, #bylineInfo .contributorNameID')
        if author_element:
            book_info['作者'] = author_element.text.strip()
            
            author_href = author_element.get('href')
            if author_href:
                if author_href.startswith('http'):
                    # 确保链接使用正确的域名
                    if 'amazon.com' in author_href and not 'amazon.co.jp' in author_href:
                        author_href = author_href.replace('amazon.com', 'amazon.co.jp')
                    book_info['作者页面'] = author_href
                else:
                    book_info['作者页面'] = "https://www.amazon.co.jp" + author_href
            else:
                book_info['作者页面'] = ""
            
            print(f"Found author using traditional selector: {book_info['作者']}")
            author_found = True
    
    # Extract cover image URL
    cover_element = soup.select_one('#imgTagWrapperId img, #imgBlkFront')
    if cover_element:
        if cover_element.get('data-old-hires'):
            book_info['封面'] = cover_element.get('data-old-hires')
        elif cover_element.get('src'):
            book_info['封面'] = cover_element.get('src')
    
    # Extract author bio
    author_bio_element = soup.select_one('._about-the-author-card_style_cardContentDiv__FXLPd, .a-expander-content')
    if author_bio_element:
        paragraphs = author_bio_element.find_all('p')
        if paragraphs:
            book_info['作者简介'] = '\n'.join([p.text.strip() for p in paragraphs])
    
    # Extract book description
    description_element = soup.select_one('#bookDescription_feature_div .a-expander-content, #productDescription')
    if description_element:
        book_info['内容简介'] = description_element.text.strip()
    
    # Extract ISBN-10 and ISBN-13
    isbn13_element = soup.select_one('#rpi-attribute-book_details-isbn13 .rpi-attribute-value, tr:has(th:contains("ISBN-13")) td')
    if isbn13_element:
        book_info['ISBN'] = isbn13_element.text.strip()
        book_id = isbn13_element.text.strip().replace('-', '')
    
    isbn10_element = soup.select_one('#rpi-attribute-book_details-isbn10 .rpi-attribute-value, tr:has(th:contains("ISBN-10")) td')
    if isbn10_element and 'ISBN' not in book_info:
        book_info['ISBN'] = isbn10_element.text.strip()
        book_id = isbn10_element.text.strip()
    
    # If still not found, try another approach
    if 'ISBN' not in book_info:
        if file_name:
            isbn_match = re.search(r'_(\d{13})_', file_name)
            if isbn_match:
                book_info['ISBN'] = isbn_match.group(1)
                book_id = isbn_match.group(1)
            else:
                isbn_match = re.search(r'(\d{13})', file_name)
                if isbn_match:
                    book_info['ISBN'] = isbn_match.group(1)
                    book_id = isbn_match.group(1)
    
    # After extracting ISBN, set the book page URL
    if url_isbn_override:
        url_isbn = url_isbn_override
    elif 'book_id' in locals():
        url_isbn = book_id
        if url_isbn.startswith('978') and len(url_isbn) > 10:
            url_isbn = url_isbn[3:]
    else:
        url_isbn = "4478106789"  # Fallback to example ISBN
    
    # Ensure the ISBN is complete and correct
    if len(url_isbn) < 10:
        url_isbn = "4478106789"
    
    # Construct Amazon URL with correct domain
    base_url = "https://www.amazon.co.jp"  # 确保始终使用JP域名
    # 对于日本亚马逊，直接使用/dp/ISBN格式，不添加书名
    book_url = f"{base_url}/dp/{url_isbn}"
    # 确保使用正确的域名
    for domain in ['amazon.com', 'amazon.co.uk']:
        if domain in book_url:
            book_url = book_url.replace(domain, "www.amazon.co.jp")
    book_info['书本页面'] = book_url
    
    # Extract publisher and publication date
    publisher_found = False
    
    # 尝试多种可能的选择器，按照优先级排序
    publisher_selectors = [
        ('div[data-rpi-attribute-name="book_details-publisher"] .rpi-attribute-value span', 'span selector'),
        ('div[data-rpi-attribute-name="book_details-publisher"] .rpi-attribute-value', 'div selector'),
        ('#rpi-attribute-book_details-publisher .rpi-attribute-value', 'attribute selector'),
        ('tr:has(th:contains("出版社")) td', 'table selector'),
        ('.a-section:contains("出版社") + .a-section span', 'section selector'),
        ('#detailBullets_feature_div li:contains("出版社") span:nth-child(2)', 'detail bullet selector'),
        ('#detailBullets_feature_div li:contains("出版社") span.a-list-item span:nth-child(2)', 'detail bullet item selector'),
        ('#detailBulletsWrapper_feature_div .a-list-item:contains("Publisher") span:not(:first-child)', 'wrapper detail selector')
    ]
    
    for selector, selector_type in publisher_selectors:
        publisher_element = soup.select_one(selector)
        if publisher_element and publisher_element.text.strip():
            # 确保不是标签文本
            if '出版社' not in publisher_element.text and '発売日' not in publisher_element.text:
                publisher_text = publisher_element.text.strip()
                # 清理日期信息
                publisher_text = re.sub(r'(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{2}/\d{2}/\d{4})', '', publisher_text)
                # 清理括号及其内容
                publisher_text = re.sub(r'\s*\([^)]*\d{4}[^)]*\)', '', publisher_text)
                publisher_text = publisher_text.strip('; :.,')
                
                if publisher_text:
                    book_info['出版社'] = publisher_text
                    print(f"Found publisher from {selector_type}: {book_info['出版社']}")
                    publisher_found = True
                    break
    
    # 如果上面的选择器都没有找到，使用旧方法的后备选项
    if not publisher_found:
        publisher_element = soup.select_one('#rpi-attribute-book_details-publisher .rpi-attribute-value')
        if publisher_element:
            # 清理日期信息
            publisher_text = publisher_element.text.strip()
            publisher_text = re.sub(r'(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{2}/\d{2}/\d{4})', '', publisher_text)
            publisher_text = re.sub(r'\s*\([^)]*\d{4}[^)]*\)', '', publisher_text)
            publisher_text = publisher_text.strip('; :.,')
            
            if publisher_text:
                book_info['出版社'] = publisher_text
                print(f"Found publisher from backup selector: {book_info['出版社']}")
                publisher_found = True
    
    # 提取出版日期
    pub_date_selectors = [
        ('#rpi-attribute-book_details-publication_date .rpi-attribute-value', 'direct selector'),
        ('div[data-rpi-attribute-name="book_details-publication_date"] .rpi-attribute-value', 'attribute selector'),
        ('tr:has(th:contains("発売日")) td', 'table selector'),
        ('tr:has(th:contains("出版日")) td', 'publisher date selector'),
        ('#detailBullets_feature_div li:contains("発売日") span:nth-child(2)', 'detail bullet selector'),
        ('#detailBullets_feature_div li:contains("出版日") span:nth-child(2)', 'pub date bullet selector')
    ]
    
    pub_date_found = False
    for selector, selector_type in pub_date_selectors:
        pub_date_element = soup.select_one(selector)
        if pub_date_element and pub_date_element.text.strip():
            book_info['出版时间'] = pub_date_element.text.strip()
            print(f"Found publication date from {selector_type}: {book_info['出版时间']}")
            pub_date_found = True
            break
    
    if not pub_date_found:
        # 尝试从其他位置提取
        publisher_element = soup.select_one('#productSubtitle')
        if publisher_element:
            subtitle_text = publisher_element.text.strip()
            pub_date_match = re.search(r'(\d+ \w+\. \d+|\d+ \w+ \d{4})', subtitle_text)
            if pub_date_match:
                book_info['出版时间'] = pub_date_match.group(1)
    
    # 新的评分提取逻辑
    rating_value = ""
    rating_count = ""

    # 直接获取评分值 
    rating_value_element = soup.select_one('#acrPopover .a-size-base.a-color-base, #acrPopover .a-icon-alt')
    if rating_value_element:
        rating_text = rating_value_element.text.strip()
        # 提取数字部分 (如 "4.3" 或 "4.3 out of 5 stars")
        rating_match = re.search(r'([\d\.]+)', rating_text)
        if rating_match:
            rating_value = rating_match.group(1)
    
    # 如果上面的选择器没有找到，尝试其他方式
    if not rating_value:
        star_element = soup.select_one('span.a-icon-alt')
        if star_element:
            rating_match = re.search(r'([\d\.]+)', star_element.text)
            if rating_match:
                rating_value = rating_match.group(1)

    # 直接获取评论数量
    rating_count_element = soup.select_one('#acrCustomerReviewText')
    if rating_count_element:
        count_text = rating_count_element.text.strip()
        # 提取数字部分 (如 "20 ratings")
        count_match = re.search(r'([\d,]+)', count_text)
        if count_match:
            rating_count = count_match.group(1)

    # 设置评分信息
    if rating_value:
        book_info['amazon_rating'] = rating_value
        if rating_count:
            book_info['amazon_rating_count'] = f"{rating_count} ratings"
    
    # 简化关联图书提取逻辑 - 直接从第一个轮播中提取
   
    related_books = []
    # 为日本域名尽量提取10-20本相关图书
    max_related_books = 20
    
    # 方法1: 从所有轮播中提取相关图书
    all_carousels = soup.select('ol.a-carousel')
    print(f"找到 {len(all_carousels)} 个轮播元素组")
    
    for carousel_index, carousel in enumerate(all_carousels[:3]):  # 限制只查找前3个轮播
        carousel_items = carousel.select('li.a-carousel-card')
        print(f"轮播 #{carousel_index+1} 中找到 {len(carousel_items)} 个项目")
        
        for item in carousel_items:
            if len(related_books) >= max_related_books:
                break
                
            book = {}
            
            # 提取书名从图片alt属性
            img = item.select_one('img')
            if img and img.get('alt'):
                book['title'] = img.get('alt').strip()
            
            # 如果找不到alt属性，尝试从其他元素获取标题
            if not book.get('title'):
                title_element = item.select_one('.p13n-sc-truncate, .a-size-base, a.a-link-normal')
                if title_element and title_element.text.strip():
                    book['title'] = title_element.text.strip()
            
            # 提取链接
            link_element = item.select_one('a')
            if link_element and link_element.get('href'):
                href = link_element.get('href')
                # 确保链接是完整的URL
                if href.startswith('/'):
                    book['url'] = f"https://www.amazon.co.jp{href}"
                elif href.startswith('http'):
                    book['url'] = href
            
            # 只添加有标题和链接的书籍
            if book.get('title') and book.get('url'):
                # 检查是否为重复书籍
                is_duplicate = False
                for existing_book in related_books:
                    if existing_book.get('title') == book.get('title'):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    related_books.append(book)
        
        if len(related_books) >= max_related_books:
            break
    
    # 方法2: 使用amazon.com的方法提取相关图书
    if len(related_books) < 10:
        print("尝试使用amazon.com的方法提取相关图书...")
        carousel_elements = soup.select('.a-carousel-card')
        print(f"找到 {len(carousel_elements)} 个轮播元素")
        
        for element in carousel_elements:
            if len(related_books) >= max_related_books:
                break
                
            link_element = element.select_one('a[href*="/dp/"]')
            image_element = element.select_one('img')
            title_element = element.select_one('.a-truncate, .p13n-sc-truncate')
            
            if link_element and image_element:
                title_text = ''
                if title_element:
                    if title_element.select_one('.a-truncate-full'):
                        title_text = title_element.select_one('.a-truncate-full').text.strip()
                    else:
                        title_text = title_element.text.strip()
                elif image_element.get('alt'):
                    title_text = image_element.get('alt', '')
                
                if title_text:
                    related_book = {
                        "title": title_text,
                        "url": urljoin(base_url, link_element.get('href', '')),
                        "image_url": image_element.get('src', '')
                    }
                    
                    # 检查是否为重复书籍
                    is_duplicate = False
                    for existing_book in related_books:
                        if existing_book.get('title') == related_book['title']:
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        related_books.append(related_book)
                        print(f"找到相关图书: {related_book['title']}")
    
    # 方法3: 从"Frequently bought together"部分提取相关图书
    if len(related_books) < 10:
        print("尝试从'Frequently bought together'部分提取相关图书...")
        frequently_bought_section = soup.select_one('div#sims-consolidated-2_feature_div, div#sims-fbt')
        if frequently_bought_section:
            fbt_items = frequently_bought_section.select('li.a-spacing-mini, .sims-fbt-image')
            for item in fbt_items:
                if len(related_books) >= max_related_books:
                    break
                    
                book = {}
                
                # 提取标题
                title_element = item.select_one('a.a-link-normal')
                if title_element:
                    if title_element.get('title'):
                        book['title'] = title_element.get('title').strip()
                    elif title_element.text.strip():
                        book['title'] = title_element.text.strip()
                
                # 如果没有找到标题，尝试从图片alt属性获取
                if not book.get('title'):
                    img = item.select_one('img')
                    if img and img.get('alt'):
                        book['title'] = img.get('alt').strip()
                
                # 提取链接
                link_element = item.select_one('a.a-link-normal')
                if link_element and link_element.get('href'):
                    href = link_element.get('href')
                    if href.startswith('/'):
                        book['url'] = f"https://www.amazon.co.jp{href}"
                    elif href.startswith('http'):
                        book['url'] = href
                
                # 只添加有标题和链接的书籍
                if book.get('title') and book.get('url'):
                    # 检查是否为重复书籍
                    is_duplicate = False
                    for existing_book in related_books:
                        if existing_book.get('title') == book.get('title'):
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        related_books.append(book)
    
    # 方法4: 检查所有可能的书籍相关区域
    if len(related_books) < 10:
        print("尝试从其他区域提取相关图书...")
        possible_sections = [
            '#similarItemsContainer', 
            '#similar-by-categories',
            '#purchase-similarities',
            '#also_bought_siblings',
            '.rhf-shoveler',
            '#pd-aw-similar',
            '.a-similar-items'
        ]
        
        for section_selector in possible_sections:
            if len(related_books) >= max_related_books:
                break
                
            section = soup.select_one(section_selector)
            if section:
                # 从区域中提取链接和图片
                item_links = section.select('a[href*="/dp/"]')
                for link in item_links:
                    if len(related_books) >= max_related_books:
                        break
                        
                    book = {}
                    
                    # 尝试从链接文本或alt属性获取标题
                    title_text = link.text.strip()
                    if not title_text:
                        img = link.select_one('img')
                        if img and img.get('alt'):
                            title_text = img.get('alt')
                    
                    if title_text:
                        book['title'] = title_text
                        href = link.get('href')
                        if href:
                            if href.startswith('/'):
                                book['url'] = f"https://www.amazon.co.jp{href}"
                            elif href.startswith('http'):
                                book['url'] = href
                            else:
                                book['url'] = urljoin(base_url, href)
                        
                        # 检查是否有效且不重复
                        if book.get('title') and book.get('url'):
                            is_duplicate = False
                            for existing_book in related_books:
                                if existing_book.get('title') == book.get('title'):
                                    is_duplicate = True
                                    break
                            
                            if not is_duplicate:
                                related_books.append(book)
    
    # 最终设置相关图书数据
    if related_books:
        print(f"总共找到 {len(related_books)} 本相关图书")
        # 确保不超过20本书
        if len(related_books) > max_related_books:
            related_books = related_books[:max_related_books]
            print(f"截取前 {max_related_books} 本相关图书")
        book_info['关联图书'] = related_books
    else:
        print("未找到相关图书")
    
    # Extract reviews
    reviews = []
    review_elements = soup.select('div[data-hook="review"]')
    
    if not review_elements:
        review_elements = soup.select('.customer-review, .review')
    
    for review_element in review_elements[:10]:
        review = {}
        
        reviewer_element = review_element.select_one('.a-profile-name')
        if reviewer_element:
            review['reviewer_name'] = reviewer_element.text.strip()
        
        rating_element = review_element.select_one('[data-hook="review-star-rating"], .a-icon-star')
        if rating_element:
            rating_text = rating_element.select_one('.a-icon-alt')
            if rating_text:
                rating_match = re.search(r'([\d\.]+)', rating_text.text)
                if rating_match:
                    review['rating'] = rating_match.group(1)
        
        title_element = review_element.select_one('[data-hook="review-title"], .review-title')
        if title_element:
            review['title'] = title_element.text.strip()
        
        date_element = review_element.select_one('[data-hook="review-date"], .review-date')
        if date_element:
            review['date'] = date_element.text.strip()
        
        text_element = review_element.select_one('[data-hook="review-body"], .review-text')
        if text_element:
            content_element = text_element.select_one('[data-hook="review-collapsed"], .review-text-content')
            if content_element:
                review['content'] = content_element.text.strip()
            else:
                review['content'] = text_element.text.strip()
        
        if review and (review.get('reviewer_name') or review.get('content')):
            reviews.append(review)
    
    if reviews:
        book_info['读者评论'] = reviews
    
    # 添加区域标识
    book_info['region'] = 'jp'
    
    return book_info

def extract_us_book_info(html_content, file_name=None, base_url=None):
    """提取美国亚马逊图书信息"""
    print("\n开始提取美国亚马逊图书信息...")
    
    # 确保base_url正确
    if not base_url or "amazon.co.uk" in base_url or "amazon.co.jp" in base_url:
        base_url = "https://www.amazon.com"
        print(f"已将base_url调整为: {base_url}")
    
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 初始化结果字典
    original_book_info = {
        "title": "",
        "author": "",
        "author_url": "",
        "publisher": "",
        "publication_date": "",
        "isbn": "",
        "cover_image_url": "",
        "description": "",
        "author_bio": "",
        "amazon_rating": "",
        "amazon_rating_count": "",
        "goodreads_rating": "",
        "goodreads_rating_count": "",
        "reviews": [],
        "related_books": [],
        "book_url": "",
        "domain": "amazon.com",
        "region": "us",
    }
    
    # 从文件名或URL中提取ISBN号（如果可能）
    url_isbn_override = None
    if file_name:
        # 尝试从文件名中提取ISBN
        dp_match = re.search(r'dp/(\d{10})', file_name)
        if dp_match:
            url_isbn_override = dp_match.group(1)
        elif re.search(r'dp/(\d{10})/', file_name):
            url_isbn_override = re.search(r'dp/(\d{10})/', file_name).group(1)
        else:
            isbn10_match = re.search(r'(?<!\d)(\d{10})(?!\d)', file_name)
            if isbn10_match:
                url_isbn_override = isbn10_match.group(1)
            else:
                isbn13_match = re.search(r'(?<!\d)(\d{13})(?!\d)', file_name)
                if isbn13_match:
                    isbn13 = isbn13_match.group(1)
                    if isbn13.startswith('978') and len(isbn13) > 10:
                        url_isbn_override = isbn13[3:12]
                    else:
                        url_isbn_override = isbn13
    
    # 1. 提取书名
    title_element = soup.select_one('#productTitle, .kindle-title, .a-size-extra-large')
    if title_element:
        original_book_info["title"] = title_element.text.strip()
        print(f"提取到标题: {original_book_info['title']}")
    else:
        print("未找到标题")
    
    # 2. 提取作者
    author_element = soup.select_one('#bylineInfo .author .a-link-normal')
    if author_element:
        original_book_info["author"] = author_element.text.strip()
        
        # 提取作者页面URL
        author_url = author_element.get('href')
        if author_url:
            if not author_url.startswith('http'):
                author_url = base_url + author_url
            original_book_info["author_url"] = author_url
            print(f"提取到作者URL: {author_url}")
        
        print(f"提取到作者: {original_book_info['author']}")
    else:
        # 尝试其他选择器
        alternative_selectors = [
            '#bylineInfo .contributorNameID',
            '.a-link-normal[href*="/e/"]',
            '#bylineInfo a.a-link-normal',
            '.author a',
            '#byline_secondary_view_div a'
        ]
        
        for selector in alternative_selectors:
            author_elements = soup.select(selector)
            if author_elements:
                for element in author_elements:
                    if element.text.strip():
                        original_book_info["author"] = element.text.strip()
                        
                        # 提取作者URL
                        author_url = element.get('href')
                        if author_url:
                            if not author_url.startswith('http'):
                                author_url = base_url + author_url
                            original_book_info["author_url"] = author_url
                            print(f"从替代选择器提取到作者URL: {author_url}")
                        
                        print(f"从替代选择器提取到作者: {original_book_info['author']}")
                        break
                if original_book_info["author"]:
                    break
    
    # 3. 提取书籍URL
    canonical_link = soup.select_one('link[rel="canonical"]')
    if canonical_link and canonical_link.get('href'):
        original_book_info["book_url"] = canonical_link.get('href')
        print(f"从canonical链接提取到书籍URL: {original_book_info['book_url']}")
    else:
        og_url = soup.select_one('meta[property="og:url"]')
        if og_url and og_url.get('content'):
            original_book_info["book_url"] = og_url.get('content')
            print(f"从og:url元标签提取到书籍URL: {original_book_info['book_url']}")
        else:
            # 尝试找到ASIN并构建URL
            asin_element = soup.select_one('input[name="ASIN"]')
            if asin_element and asin_element.get('value'):
                asin = asin_element.get('value')
                original_book_info["book_url"] = f"{base_url}/dp/{asin}"
                print(f"从ASIN构建书籍URL: {original_book_info['book_url']}")
            else:
                print("未找到书籍URL")
    
    # 4. 提取ISBN
    isbn13_element = soup.select_one('#rpi-attribute-book_details-isbn13 .rpi-attribute-value, tr:has(th:contains("ISBN-13")) td')
    if isbn13_element:
        original_book_info["isbn"] = isbn13_element.text.strip()
        print(f"提取到ISBN-13: {original_book_info['isbn']}")
    
    isbn10_element = soup.select_one('#rpi-attribute-book_details-isbn10 .rpi-attribute-value, tr:has(th:contains("ISBN-10")) td')
    if isbn10_element:
        if not original_book_info["isbn"]:  # 如果没有ISBN-13，使用ISBN-10
            original_book_info["isbn"] = isbn10_element.text.strip()
        # 优先使用ISBN-10作为isbn10字段
        original_book_info["isbn10"] = isbn10_element.text.strip()
        print(f"提取到ISBN-10: {original_book_info['isbn10']}")
    
    # 如果HTML中没有找到ISBN，尝试从文件名提取
    if not original_book_info["isbn"] and file_name:
        isbn_match = re.search(r'_(\d{13})_', file_name)
        if isbn_match:
            original_book_info["isbn"] = isbn_match.group(1)
            print(f"从文件名提取到ISBN: {original_book_info['isbn']}")
        else:
            isbn_match = re.search(r'(\d{13})', file_name)
            if isbn_match:
                original_book_info["isbn"] = isbn_match.group(1)
                print(f"从文件名提取到ISBN: {original_book_info['isbn']}")
    
    # 如果还是没有ISBN，使用override作为后备
    if not original_book_info["isbn"] and url_isbn_override:
        original_book_info["isbn"] = url_isbn_override
        print(f"使用备选ISBN: {original_book_info['isbn']}")
    
    # 5. 提取出版社和出版日期
    # 尝试提取出版社
    publisher_element = soup.select_one('#rpi-attribute-book_details-publisher .rpi-attribute-value span, #rpi-attribute-book_details-publisher .rpi-attribute-value')
    if publisher_element:
        original_book_info["publisher"] = publisher_element.text.strip()
        print(f"提取到出版社: {original_book_info['publisher']}")
    else:
        # 尝试从详细信息中提取
        detail_elements = soup.select('#detailBullets_feature_div li, #productDetailsTable li')
        for detail in detail_elements:
            detail_text = detail.text.strip().lower()
            if 'publisher' in detail_text:
                publisher_text = detail_text.split(':', 1)[1].strip() if ':' in detail_text else detail_text
                # 清理出版社文本
                publisher_text = re.sub(r'(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{4}/\d{1,2}/\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{1,2}-\d{1,2})', '', publisher_text)
                publisher_text = re.sub(r'\((出版|published|release).+?\)', '', publisher_text)
                publisher_text = publisher_text.strip('; :.,')
                
                if publisher_text:
                    original_book_info["publisher"] = publisher_text.strip()
                    print(f"从详细信息提取到出版社: {original_book_info['publisher']}")
                    break
    
    # 尝试提取出版日期
    pub_date_element = soup.select_one('#rpi-attribute-book_details-publication_date .rpi-attribute-value')
    if pub_date_element:
        original_book_info["publication_date"] = pub_date_element.text.strip()
        print(f"提取到出版日期: {original_book_info['publication_date']}")
    else:
        # 尝试从详细信息中提取
        for detail in detail_elements:
            detail_text = detail.text.strip().lower()
            if 'publication date' in detail_text or 'published' in detail_text or 'release date' in detail_text:
                date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{4}/\d{1,2}/\d{1,2}|\d{4}-\d{1,2}-\d{1,2})', detail_text)
                if date_match:
                    original_book_info["publication_date"] = date_match.group(1)
                    print(f"从详细信息提取到出版日期: {original_book_info['publication_date']}")
                    break
    
    # 6. 提取封面图片URL
    image_element = soup.select_one('#imgTagWrapperId img, #imgBlkFront, #ebooksImgBlkFront, #imageBlock img, #ebooks-img-canvas img')
    if image_element:
        original_book_info["cover_image_url"] = image_element.get('src', '')
        print(f"提取到封面图片URL: {original_book_info['cover_image_url']}")
    else:
        print("未找到封面图片")
    
    # 7. 提取图书描述
    description_element = soup.select_one('#bookDescription_feature_div .a-expander-content')
    if description_element:
        original_book_info["description"] = description_element.text.strip()
        print(f"提取到图书描述: {original_book_info['description'][:50]}...")
    else:
        # 尝试其他常见位置
        description_elements = [
            soup.select_one('#productDescription .content'),
            soup.select_one('#bookDescription_feature_div noscript'),
            soup.select_one('#bookDescription_feature_div'),
            soup.select_one('#book-description')
        ]
        
        for element in description_elements:
            if element and element.text.strip():
                original_book_info["description"] = element.text.strip()
                print(f"从替代来源提取到图书描述: {original_book_info['description'][:50]}...")
                break
        
        # 尝试从编辑评论中查找描述
        if not original_book_info["description"]:
            editorial_reviews = soup.select('#editorialReviews_feature_div .a-section')
            for review in editorial_reviews:
                heading = review.find_previous('h3')
                if heading and 'About the Author' not in heading.text:
                    description = review.text.strip()
                    if len(description) > 100:  # 确保内容足够长
                        original_book_info["description"] = description
                        print(f"从编辑评论提取到图书描述: {description[:50]}...")
                        break
    
    # 8. 提取作者简介
    author_bio_element = soup.select_one('._about-the-author-card_carouselItemStyles_expander__3Fm-M .a-cardui-content, #authorBio_feature_div, .author-biography')
    if author_bio_element:
        original_book_info["author_bio"] = author_bio_element.text.strip()
        print(f"提取到作者简介: {original_book_info['author_bio'][:50]}...")
    else:
        # 尝试从编辑评论中查找作者简介
        editorial_reviews = soup.select('#editorialReviews_feature_div .a-section')
        for review in editorial_reviews:
            heading = review.find_previous('h3')
            if heading and 'About the Author' in heading.text:
                author_bio = review.text.strip()
                original_book_info["author_bio"] = author_bio
                print(f"从编辑评论提取到作者简介: {author_bio[:50]}...")
                break
    
    # 9. 提取评分信息
    rating_element = soup.select_one('#acrPopover')
    if rating_element:
        rating_text = rating_element.get('title', '')
        rating_match = re.search(r'(\d+\.\d+|\d+)', rating_text)
        if rating_match:
            original_book_info["amazon_rating"] = rating_match.group(1)
            print(f"提取到亚马逊评分: {original_book_info['amazon_rating']}")
    
    # 尝试提取评分数量
    rating_count_element = soup.select_one('#acrCustomerReviewText')
    if rating_count_element:
        count_text = rating_count_element.text.strip()
        count_match = re.search(r'(\d+[\d,]*)', count_text)
        if count_match:
            original_book_info["amazon_rating_count"] = count_match.group(1)
            print(f"提取到亚马逊评分数量: {original_book_info['amazon_rating_count']}")
    
    # 10. 提取评论
    review_elements = soup.select('.review')
    print(f"找到 {len(review_elements)} 个评论元素")
    
    seen_reviews = set()  # 避免重复评论
    
    for element in review_elements:
        reviewer_element = element.select_one('.a-profile-name')
        rating_element = element.select_one('.review-rating')
        title_element = element.select_one('.review-title')
        date_element = element.select_one('.review-date')
        text_element = element.select_one('.review-text')
        
        if reviewer_element and text_element:
            reviewer = reviewer_element.text.strip()
            rating = rating_element.text.strip() if rating_element else ""
            title = title_element.text.strip() if title_element else ""
            date = date_element.text.strip() if date_element else ""
            content = text_element.text.strip()
            
            # 创建评论的唯一键以避免重复
            review_key = f"{reviewer}:{title}:{content[:50]}"
            
            if review_key not in seen_reviews:
                seen_reviews.add(review_key)
                
                # 提取评分值
                rating_value = ""
                rating_match = re.search(r'(\d+(\.\d+)?)', rating)
                if rating_match:
                    rating_value = rating_match.group(1)
                
                review_data = {
                    "reviewer_name": reviewer,
                    "rating": rating_value,
                    "title": title,
                    "date": date,
                    "content": content
                }
                
                original_book_info["reviews"].append(review_data)
                print(f"提取到评论 {len(original_book_info['reviews'])}: {rating} {title[:20]}...")
                
                # 限制为10条评论
                if len(original_book_info["reviews"]) >= 10:
                    break
    
    # 11. 提取相关图书
    carousel_elements = soup.select('.a-carousel-card')
    print(f"找到 {len(carousel_elements)} 个轮播元素")
    
    for element in carousel_elements:
        link_element = element.select_one('a[href*="/dp/"]')
        image_element = element.select_one('img')
        title_element = element.select_one('.a-truncate, .p13n-sc-truncate')
        
        if link_element and image_element:
            title_text = ''
            if title_element:
                if title_element.select_one('.a-truncate-full'):
                    title_text = title_element.select_one('.a-truncate-full').text.strip()
                else:
                    title_text = title_element.text.strip()
            elif image_element.get('alt'):
                title_text = image_element.get('alt', '')
            
            if title_text:
                related_book = {
                    "title": title_text,
                    "url": urljoin(base_url, link_element.get('href', '')),
                    "image_url": image_element.get('src', '')
                }
                original_book_info["related_books"].append(related_book)
                print(f"提取到相关图书: {related_book['title']}")
    
    # 打印提取结果概要
    field_count = len([k for k, v in original_book_info.items() if v and not (isinstance(v, list) and len(v) == 0)])
    print(f"\n从美国亚马逊提取到的字段数: {field_count}")
    print(f"评论数: {len(original_book_info['reviews'])}")
    print(f"相关图书数: {len(original_book_info['related_books'])}")
    
    return original_book_info

def standardize_book_info(book_info, region):
    """确保不同区域提取的数据格式一致"""
    standard_info = {}
    
    # 基本字段映射，确保所有重要字段都有统一的键名
    field_mappings = {
        "书名": ["书名", "title", "book_title"],
        "作者": ["作者", "author", "authors"],
        "作者页面": ["作者页面", "author_url"],
        "出版社": ["出版社", "publisher"],
        "出版时间": ["出版时间", "publication_date"],
        "ISBN": ["ISBN", "isbn"],
        "封面": ["封面", "cover_image_url", "imageUrl"],
        "内容简介": ["内容简介", "description"],
        "作者简介": ["作者简介", "author_bio"],
        "书本页面": ["书本页面", "book_url", "url"],
        "关联图书": ["关联图书", "related_books"],
        "读者评论": ["读者评论", "reviews"],
        "评分": ["评分", "rating"]
    }
    
    # 按照映射填充标准格式
    for standard_key, possible_keys in field_mappings.items():
        for key in possible_keys:
            if key in book_info and book_info[key]:
                standard_info[standard_key] = book_info[key]
                break
    
    # 确保关联图书的格式一致
    if "关联图书" in standard_info and isinstance(standard_info["关联图书"], list):
        formatted_related_books = []
        for book in standard_info["关联图书"]:
            if isinstance(book, dict) and "title" in book and "url" in book:
                formatted_related_books.append(book)
            elif isinstance(book, str) and " - " in book:
                title, url = book.split(" - ", 1)
                formatted_related_books.append({"title": title, "url": url})
        standard_info["关联图书"] = formatted_related_books
    
    # 添加区域信息
    standard_info["region"] = region
    
    return standard_info

def ensure_correct_domain(url, region):
    """确保URL使用正确的域名，基于区域设置"""
    domain_mapping = {
        "us": "www.amazon.com",
        "uk": "www.amazon.co.uk", 
        "jp": "www.amazon.co.jp"
    }
    
    correct_domain = domain_mapping.get(region, "www.amazon.com")
    
    # 检查URL中是否包含任何亚马逊域名
    for domain in domain_mapping.values():
        if domain in url and domain != correct_domain:
            return url.replace(domain, correct_domain)
    
    return url

def extract_from_file(file_path, region=None, domain=None):
    """Extract book information from a local HTML file."""
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist.")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except UnicodeDecodeError:
        try:
            # Try with a different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                html_content = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
    
    # Detect domain if not provided
    if not domain:
        url_match = re.search(r'https://www\.amazon\.(com|co\.uk|co\.jp)', html_content)
        if url_match:
            domain = f"amazon.{url_match.group(1)}"
            print(f"Detected domain: {domain}")
        elif region:
            # 修复：使用域名映射，而不是未定义的函数
            domain_mapping = {
                "us": "amazon.com",
                "uk": "amazon.co.uk",
                "jp": "amazon.co.jp"
            }
            domain = domain_mapping.get(region, "amazon.com")
            print(f"Using domain {domain} based on region {region}")
        else:
            domain = "amazon.com"  # Default to amazon.com
            print(f"No domain detected in HTML, defaulting to {domain}")

    # 提取数据
    book_info = extract_book_info_from_html(html_content, file_name=file_path, domain=domain)
    
    # 添加元数据以帮助调试
    if book_info:
        # 添加域名和区域信息
        book_info['domain'] = domain
        if region:
            book_info['region'] = region
        else:
            if 'co.uk' in domain:
                book_info['region'] = 'uk'
            elif 'co.jp' in domain:
                book_info['region'] = 'jp'
            else:
                book_info['region'] = 'us'
        
        # 添加文件路径信息（仅保留文件名部分以保护隐私）
        book_info['file_name'] = os.path.basename(file_path)
        
        # 添加处理时间戳
        book_info['processed_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return book_info

def main():
    """Main function to handle command-line arguments."""
    parser = argparse.ArgumentParser(description='Extract book information from Amazon product page and save to JSON file.')
    parser.add_argument('html_file', help='Path to the HTML file or URL of the Amazon product page')
    parser.add_argument('--output', default='book_info.json', help='Output JSON file path (default: book_info.json)')
    parser.add_argument('--webhook', help='Feishu webhook URL (optional, use feishu_webhook.py for sending)')
    parser.add_argument('--domain', help='Amazon domain (e.g., amazon.com, amazon.co.uk, amazon.co.jp)')
    
    args = parser.parse_args()
    
    # Check if input is a URL or a file
    if args.html_file.startswith('http'):
        # Extract from URL
        book_info = extract_from_url(args.html_file, domain=args.domain)
    else:
        # Extract from file
        book_info = extract_from_file(args.html_file, domain=args.domain)
    
    # Save to JSON file
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(book_info, f, ensure_ascii=False, indent=2)
    print(f"书籍信息已保存到 {args.output}")
    
    # 如果提供了webhook URL，提示用户如何使用feishu_webhook.py发送
    if args.webhook:
        print(f"\n如需发送到飞书webhook，请使用以下命令:")
        print(f"python feishu_webhook.py --input {args.output} --webhook {args.webhook}")
        print("\n或者直接导入feishu_webhook模块使用其send_to_feishu函数:")
        print("from feishu_webhook import send_to_feishu")
        print(f"send_to_feishu('{args.output}', '{args.webhook}')")
    
    return book_info

if __name__ == "__main__":
    main()
