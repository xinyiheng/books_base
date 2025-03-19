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
    """
    Extract book information from HTML content based on region
    """
    # 从HTML内容或提供的domain参数直接检测区域
    region = "us"  # 默认为美国
    
    # 首先尝试使用前端提供的domain参数确定区域
    if domain:
        if "amazon.co.uk" in domain:
            region = "uk"
            base_url = "https://www.amazon.co.uk"
        elif "amazon.co.jp" in domain:
            region = "jp"
            base_url = "https://www.amazon.co.jp"
        elif "amazon.com" in domain:
            region = "us"
            base_url = "https://www.amazon.com"
        print(f"从前端提供的域名参数检测到区域: {region}, 域名: {domain}")
    # 如果没有domain参数，尝试从HTML内容检测
    elif "amazon.co.uk" in html_content:
        region = "uk"
        base_url = "https://www.amazon.co.uk"
        print(f"从HTML内容检测到区域: {region}")
    elif "amazon.co.jp" in html_content:
        region = "jp"
        base_url = "https://www.amazon.co.jp"
        print(f"从HTML内容检测到区域: {region}")
    else:
        print(f"未检测到特定区域，使用默认区域: {region}")
    
    # 根据区域调用相应的提取函数，并传递文件名和base_url
    if region == "uk":
        book_info = extract_uk_book_info(html_content, file_name, base_url=base_url)
        # 确保书本页面和作者页面URL使用正确域名
        if book_info.get('书本页面'):
            book_info['书本页面'] = ensure_correct_domain(book_info['书本页面'], 'uk')
        if book_info.get('作者页面'):
            book_info['作者页面'] = ensure_correct_domain(book_info['作者页面'], 'uk')
        return book_info
    elif region == "jp":
        book_info = extract_jp_book_info(html_content, file_name, base_url=base_url)
        # 确保书本页面和作者页面URL使用正确域名
        if book_info.get('书本页面'):
            book_info['书本页面'] = ensure_correct_domain(book_info['书本页面'], 'jp')
        if book_info.get('作者页面'):
            book_info['作者页面'] = ensure_correct_domain(book_info['作者页面'], 'jp')
        return book_info
    
    # 原始的US提取逻辑保持不变
    # Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Detect language and region from base_url
    language = "en"  # Default to English
    
    print(f"Extracting book info for region: {region}, language: {language}")
    
    # First, extract all information in the original format
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
        "book_url": "",  # 添加书本页面URL字段
        "region": region,  # Store the detected region
        "language": language  # Store the detected language
    }
    
    # 为US版本添加从文件名提取ISBN的代码
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
    
    # Extract book title
    title_element = soup.select_one('#productTitle, .kindle-title, .a-size-extra-large')
    if title_element:
        original_book_info["title"] = title_element.text.strip()
        print(f"Found title: {original_book_info['title']}")
    else:
        print("Title not found")
    
    # Extract author - Add Japan-specific selectors
    author_found = False
    
    # Region-specific author selectors
    if region == "jp":
        # Try Japan-specific selectors first
        jp_author_selectors = [
            '.author a',
            '#bylineInfo .author-name',
            '#bylineInfo a[data-asin]',
            '#contributorLink',
            '.a-profile-name',
            '#byline a.contributorNameID'
        ]
        
        for selector in jp_author_selectors:
            author_element = soup.select_one(selector)
            if author_element and author_element.text.strip():
                original_book_info["author"] = author_element.text.strip()
                
                # Extract author URL
                author_url = author_element.get('href')
                if author_url:
                    if not author_url.startswith('http'):
                        author_url = base_url + author_url
                    original_book_info["author_url"] = author_url
                
                print(f"Found author (JP-specific): {original_book_info['author']}")
                author_found = True
                break
    
    # If author not found, try the standard approach
    if not author_found:
        author_element = soup.select_one('#bylineInfo .author .a-link-normal')
        if author_element:
            original_book_info["author"] = author_element.text.strip()
            
            # Extract author URL
            author_url = author_element.get('href')
            if author_url:
                if not author_url.startswith('http'):
                    author_url = base_url + author_url
                original_book_info["author_url"] = author_url
                print(f"Found author URL: {author_url}")
                
            print(f"Found author: {original_book_info['author']}")
            author_found = True
    
    # If author still not found, try alternative selectors
    if not author_found:
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
                        
                        # Extract author URL
                        author_url = element.get('href')
                        if author_url:
                            if not author_url.startswith('http'):
                                author_url = base_url + author_url
                            original_book_info["author_url"] = author_url
                            print(f"Found author URL from alternative selector: {author_url}")
                        
                        print(f"Found author from alternative selector: {original_book_info['author']}")
                        author_found = True
                        break
                if author_found:
                    break
    
    # If still not found, try to extract from filename
    if not author_found:
        filename = file_name or ""
        author_match = re.search(r'_([^_]+)_\d+', filename)
        if author_match:
            original_book_info["author"] = author_match.group(1)
            print(f"Found author from filename: {original_book_info['author']}")
        else:
            print("Author not found")

    # Extract book URL from canonical link or og:url meta tag
    canonical_link = soup.select_one('link[rel="canonical"]')
    if canonical_link and canonical_link.get('href'):
        original_book_info["book_url"] = canonical_link.get('href')
        print(f"Found book URL from canonical link: {original_book_info['book_url']}")
    else:
        og_url = soup.select_one('meta[property="og:url"]')
        if og_url and og_url.get('content'):
            original_book_info["book_url"] = og_url.get('content')
            print(f"Found book URL from og:url meta: {original_book_info['book_url']}")
        else:
            # Try to find ASIN and construct URL
            asin_element = soup.select_one('input[name="ASIN"]')
            if asin_element and asin_element.get('value'):
                asin = asin_element.get('value')
                original_book_info["book_url"] = f"{base_url}/dp/{asin}"
                print(f"Constructed book URL from ASIN: {original_book_info['book_url']}")
            else:
                print("Book URL not found")
    
    # Extract ISBN-10 and ISBN-13
    isbn13_element = soup.select_one('#rpi-attribute-book_details-isbn13 .rpi-attribute-value, tr:has(th:contains("ISBN-13")) td')
    if isbn13_element:
        original_book_info["ISBN"] = isbn13_element.text.strip()
        book_id = isbn13_element.text.strip().replace('-', '')
    
    isbn10_element = soup.select_one('#rpi-attribute-book_details-isbn10 .rpi-attribute-value, tr:has(th:contains("ISBN-10")) td')
    if isbn10_element and 'ISBN' not in original_book_info:
        original_book_info["ISBN"] = isbn10_element.text.strip()
        book_id = isbn10_element.text.strip()
    
    # If still not found, try another approach
    if 'ISBN' not in original_book_info:
        if file_name:
            isbn_match = re.search(r'_(\d{13})_', file_name)
            if isbn_match:
                original_book_info["ISBN"] = isbn_match.group(1)
                book_id = isbn_match.group(1)
            else:
                isbn_match = re.search(r'(\d{13})', file_name)
                if isbn_match:
                    original_book_info["ISBN"] = isbn_match.group(1)
                    book_id = isbn_match.group(1)
    
    # After extracting ISBN, set the book page URL
    if url_isbn_override:
        url_isbn = url_isbn_override
    elif 'book_id' in locals():
        url_isbn = book_id
        if url_isbn.startswith('978') and len(url_isbn) > 10:
            url_isbn = url_isbn[3:]
    else:
        url_isbn = "1847941834"  # Fallback to example ISBN
    
    # Ensure the ISBN is complete
    if len(url_isbn) < 10:
        url_isbn = "1847941834"
    
    # Construct Amazon URL with correct domain
    if '书名' in original_book_info:
        url_title = re.sub(r'[^\w\s-]', '', original_book_info['书名'])
        url_title = re.sub(r'\s+', '-', url_title.strip())
        book_url = f"{base_url}/{url_title}/dp/{url_isbn}"
        # 检查URL中是否有不匹配的域名
        for domain in ['amazon.com', 'amazon.co.uk', 'amazon.co.jp']:
            if domain in book_url and domain not in base_url:
                correct_domain = base_url.split('//')[1]
                book_url = book_url.replace(domain, correct_domain)
        original_book_info["book_url"] = book_url
    else:
        book_url = f"{base_url}/dp/{url_isbn}"
        # 检查URL中是否有不匹配的域名
        for domain in ['amazon.com', 'amazon.co.uk', 'amazon.co.jp']:
            if domain in book_url and domain not in base_url:
                correct_domain = base_url.split('//')[1]
                book_url = book_url.replace(domain, correct_domain)
        original_book_info["book_url"] = book_url
    
    # Extract publisher and publication date
    pub_date_found = False
    publisher_found = False

    # 首先尝试直接从 rpi-attribute-value 中提取 publisher 信息
    publisher_element = soup.select_one('#rpi-attribute-book_details-publisher .rpi-attribute-value span')
    if publisher_element and publisher_element.text.strip():
        original_book_info["publisher"] = publisher_element.text.strip()
        print(f"Found publisher from direct span selector: {original_book_info['publisher']}")
        publisher_found = True
    else:
        # 尝试不带 span 的版本
        publisher_element = soup.select_one('#rpi-attribute-book_details-publisher .rpi-attribute-value')
        if publisher_element and publisher_element.text.strip():
            original_book_info["publisher"] = publisher_element.text.strip()
            print(f"Found publisher from direct selector: {original_book_info['publisher']}")
            publisher_found = True

    # Look for publication date and publisher in detail elements
    detail_elements = soup.select('#detailBullets_feature_div li, #productDetailsTable li, #bookDetails_feature_div .detail-bullet, .book-details-section .detail-bullet, .a-unordered-list li, #detailsListWrapper .a-nostyle li, #rpi-attribute-book_details-publisher, #rpi-attribute-book_details-publication_date')
    
    # Try to extract from standard product details
    for detail in detail_elements:
        detail_text = detail.text.strip().lower()
        
        # Handle publication date
        if ('publication date' in detail_text or 'published' in detail_text or 
            'release date' in detail_text or '出版日' in detail_text):
            
            # Get the text after the label
            detail_value = None
            # 先尝试找下一个兄弟节点
            if detail.find_next_sibling():
                detail_value = detail.find_next_sibling().text.strip()
            # 如果没有找到，尝试从父节点获取
            if not detail_value or len(detail_value) < 2:
                parent_text = detail.parent.text.strip()
                # 移除当前节点的文本
                detail_value = parent_text.replace(detail.text.strip(), '').strip()
            
            if detail_value:
                # 提取出版日期
                if ('publication date' in detail_text or 'published' in detail_text or 
                    'release date' in detail_text or '出版日' in detail_text) and not pub_date_found:
                    # 尝试多种日期格式
                    date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{4}/\d{1,2}/\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{1,2}-\d{1,2})', detail_value)
                    if date_match:
                        original_book_info["publication_date"] = date_match.group(1)
                        print(f"Found publication date: {original_book_info['publication_date']}")
                        pub_date_found = True
                
                # 提取出版社
                if ('publisher' in detail_text or '出版社' in detail_text) and not publisher_found:
                    # 清理出版社文本
                    publisher_text = detail_value
                    # 移除可能的日期部分，但保留出版社名称
                    publisher_text = re.sub(r'(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{4}/\d{1,2}/\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{1,2}-\d{1,2})', '', publisher_text)
                    # 更谨慎地处理括号，只移除特定类型的括号内容
                    publisher_text = re.sub(r'\((出版|published|release).+?\)', '', publisher_text)
                    publisher_text = publisher_text.strip('; :.,')
                    
                    if publisher_text:
                        original_book_info["publisher"] = publisher_text.strip()
                        print(f"Found publisher: {original_book_info['publisher']}")
                        publisher_found = True

    # Try direct attribute selectors
    if not pub_date_found:
        pub_date_element = soup.select_one('#rpi-attribute-book_details-publication_date .rpi-attribute-value')
        if pub_date_element:
            original_book_info["publication_date"] = pub_date_element.text.strip()
            print(f"Found publication date from direct attribute: {original_book_info['publication_date']}")
            pub_date_found = True

    # 尝试特别针对日本亚马逊的方式提取出版社信息
    if not publisher_found:
        # 尝试查找特定格式的出版社元素
        jp_publisher_elements = [
            soup.select_one('div[data-rpi-attribute-name="book_details-publisher"] .rpi-attribute-value span'),
            soup.select_one('div[data-rpi-attribute-name="book_details-publisher"] .rpi-attribute-value'),
            soup.select_one('#rpi-attribute-book_details-publisher .rpi-attribute-value'),
            soup.select_one('tr:has(th:contains("出版社")) td'),
            soup.select_one('.a-section:contains("出版社") + .a-section .a-text-bold')
        ]
        
        for element in jp_publisher_elements:
            if element and element.text.strip():
                original_book_info["publisher"] = element.text.strip()
                print(f"Found publisher with JP-specific selector: {original_book_info['publisher']}")
                publisher_found = True
                break

    # Additional cleanup for publisher - remove "発売日" and related text if it got captured incorrectly
    if 'publisher' in original_book_info and ('発売日' in original_book_info['publisher'] or '出版社' in original_book_info['publisher']):
        # This indicates we've captured a label instead of the value - try more specific selector
        publisher_element = soup.select_one('div[data-rpi-attribute-name="book_details-publisher"] .rpi-attribute-value span')
        if publisher_element and publisher_element.text.strip():
            # 确保不是标签文本
            if '出版社' not in publisher_element.text and '発売日' not in publisher_element.text:
                original_book_info["publisher"] = publisher_element.text.strip()
                print(f"Found publisher with corrected selector: {original_book_info['publisher']}")
                publisher_found = True
    
    # 确保publisher字段大小写统一
    if 'Publisher' in original_book_info and 'publisher' not in original_book_info:
        original_book_info['publisher'] = original_book_info['Publisher']
    elif 'publisher' in original_book_info and 'Publisher' not in original_book_info:
        original_book_info['Publisher'] = original_book_info['publisher']
    
    # 确保publication_date字段大小写统一
    if 'Publication_date' in original_book_info and 'publication_date' not in original_book_info:
        original_book_info['publication_date'] = original_book_info['Publication_date']
    elif 'publication_date' in original_book_info and 'Publication_date' not in original_book_info:
        original_book_info['Publication_date'] = original_book_info['publication_date']
    
    # Extract cover image URL
    image_element = soup.select_one('#imgTagWrapperId img, #imgBlkFront, #ebooksImgBlkFront, #imageBlock img, #ebooks-img-canvas img')
    if image_element:
        original_book_info["cover_image_url"] = image_element.get('src', '')
        print(f"Found cover image URL: {original_book_info['cover_image_url']}")
    else:
        print("Cover image not found")
    
    # Extract book description
    description_element = soup.select_one('#bookDescription_feature_div .a-expander-content')
    if description_element:
        original_book_info["description"] = description_element.text.strip()
        print(f"Found description: {original_book_info['description'][:50]}...")
    else:
        # Try to find description from other common locations
        description_elements = [
            soup.select_one('#productDescription .content'),
            soup.select_one('#bookDescription_feature_div noscript'),
            soup.select_one('#bookDescription_feature_div'),
            soup.select_one('#book-description')
        ]
        
        for element in description_elements:
            if element and element.text.strip():
                original_book_info["description"] = element.text.strip()
                print(f"Found description from alternative source: {original_book_info['description'][:50]}...")
                break
        
        # Try to find description from editorial reviews
        if "description" not in original_book_info or not original_book_info["description"]:
            editorial_reviews = soup.select('#editorialReviews_feature_div .a-section.a-spacing-small.a-padding-small')
            for review in editorial_reviews:
                # Look for sections with book description (not about author)
                heading = review.find_previous('h3')
                if heading and 'About the Author' not in heading.text:
                    description = review.text.strip()
                    if len(description) > 100:  # Ensure it's substantial enough to be a description
                        original_book_info["description"] = description
                        print(f"Found description from editorial reviews: {description[:50]}...")
                        break
        
        if "description" not in original_book_info or not original_book_info["description"]:
            print("Description not found")
    
    # Extract author bio
    author_bio_element = soup.select_one('._about-the-author-card_carouselItemStyles_expander__3Fm-M .a-cardui-content, #authorBio_feature_div, .author-biography')
    if author_bio_element:
        original_book_info["author_bio"] = author_bio_element.text.strip()
        print(f"Found author bio: {original_book_info['author_bio'][:50]}...")
    else:
        # Try to find author bio from editorial reviews
        editorial_reviews = soup.select('#editorialReviews_feature_div .a-section.a-spacing-small.a-padding-small')
        for review in editorial_reviews:
            # Look for sections with "About the Author" heading
            heading = review.find_previous('h3')
            if heading and 'About the Author' in heading.text:
                author_bio = review.text.strip()
                original_book_info["author_bio"] = author_bio
                print(f"Found author bio from editorial reviews: {author_bio[:50]}...")
                break
        
        if "author_bio" not in original_book_info:
            print("Author bio not found")
    
    # Try to find rating
    rating_element = soup.select_one('#acrPopover')
    if rating_element:
        rating_text = rating_element.get('title', '')
        rating_match = re.search(r'(\d+\.\d+|\d+)', rating_text)
        if rating_match:
            rating = rating_match.group(1)
            original_book_info["amazon_rating"] = rating
            print(f"Found Amazon rating: {rating}")
    
    # If rating not found, try to find from detail bullets or other locations
    if 'amazon_rating' not in original_book_info:
        rating_elements = soup.select('.a-icon-star, .a-star-medium-4-5, .a-star-medium-4, .a-star-medium-5')
        for element in rating_elements:
            rating_text = element.get_text().strip()
            rating_match = re.search(r'(\d+\.\d+|\d+)', rating_text)
            if rating_match:
                rating = rating_match.group(1)
                original_book_info["amazon_rating"] = rating
                print(f"Found Amazon rating from stars: {rating}")
                break
    
    # Extract Amazon rating count
    rating_count_element = soup.select_one('#acrCustomerReviewText')
    if rating_count_element:
        count_text = rating_count_element.text.strip()
        count_match = re.search(r'(\d+[\d,]*)', count_text)
        if count_match:
            original_book_info["amazon_rating_count"] = count_match.group(1) + " ratings"
            print(f"Found Amazon rating count: {original_book_info['amazon_rating_count']}")
    
    # Extract Goodreads rating if available
    goodreads_element = soup.select_one('.gdrRatingStyle')
    if goodreads_element:
        goodreads_text = goodreads_element.text.strip()
        goodreads_rating_match = re.search(r'(\d+(\.\d+)?)', goodreads_text)
        if goodreads_rating_match:
            original_book_info["goodreads_rating"] = goodreads_rating_match.group(1)
            print(f"Found Goodreads rating: {original_book_info['goodreads_rating']}")
    
    goodreads_count_element = soup.select_one('.gdrRatingCount')
    if goodreads_count_element:
        goodreads_count_text = goodreads_count_element.text.strip()
        goodreads_count_match = re.search(r'(\d+[\d,]*)', goodreads_count_text)
        if goodreads_count_match:
            original_book_info["goodreads_rating_count"] = goodreads_count_match.group(1) + " ratings"
            print(f"Found Goodreads rating count: {original_book_info['goodreads_rating_count']}")
    
    # Extract reader reviews
    review_elements = soup.select('.review')
    print(f"Found {len(review_elements)} review elements")
    
    seen_reviews = set()  # To avoid duplicate reviews
    
    for element in review_elements:
        reviewer_element = element.select_one('.a-profile-name')
        rating_element = element.select_one('.review-rating')
        title_element = element.select_one('.review-title')
        date_element = element.select_one('.review-date')
        content_element = element.select_one('.review-text')
        helpful_element = element.select_one('.cr-vote-text')
        
        if reviewer_element and content_element:
            reviewer = reviewer_element.text.strip()
            rating = rating_element.text.strip() if rating_element else ""
            title = title_element.text.strip() if title_element else ""
            date = date_element.text.strip() if date_element else ""
            content = content_element.text.strip()
            helpful = helpful_element.text.strip() if helpful_element else ""
            
            # Create a unique key for this review to avoid duplicates
            review_key = f"{reviewer}:{title}:{content[:50]}"
            
            if review_key not in seen_reviews:
                seen_reviews.add(review_key)
                
                # Extract rating value (e.g., "5.0" from "5.0 out of 5 stars")
                rating_value = ""
                rating_match = re.search(r'(\d+(\.\d+)?)', rating)
                if rating_match:
                    rating_value = rating_match.group(1)
                
                review_data = {
                    "reviewer_name": reviewer,
                    "rating": rating_value,
                    "title": title,
                    "date": date,
                    "content": content,
                    "helpful_votes": helpful
                }
                
                original_book_info["reviews"].append(review_data)
                print(f"Found review {len(original_book_info['reviews'])}: {rating} {title[:20]}...")
                
                # Limit to 10 reviews
                if len(original_book_info["reviews"]) >= 10:
                    break
    
    print(f"Total unique reviews extracted: {len(original_book_info['reviews'])}")
    
    # Extract related books
    carousel_elements = soup.select('.a-carousel-card')
    print(f"Found {len(carousel_elements)} carousel elements")
    
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
                print(f"Found related book: {related_book['title']}")
    
    return original_book_info

def convert_to_feishu_format(original_book_info):
    """Convert book information to Feishu format"""
    # 创建飞书卡片格式
    feishu_data = {
        "标题": original_book_info.get('title', ''),
        "书名": original_book_info.get('title', ''),
        "作者": original_book_info.get('author', ''),
        "作者页面": original_book_info.get('author_url', ''),
        "出版社": original_book_info.get('publisher', ''),
        "出版时间": original_book_info.get('publication_date', ''),
        "ISBN": original_book_info.get('isbn', ''),
        "封面": original_book_info.get('cover_image_url', ''),
        "内容简介": original_book_info.get('description', ''),
        "作者简介": original_book_info.get('author_bio', ''),
        "评分": '',
        "书本页面": original_book_info.get('book_url', ''),
        "相关图书": original_book_info.get('related_books', []),
        "评论": original_book_info.get('reviews', []),
    }
    
    # 添加亚马逊评分和Goodreads评分
    amazon_rating = original_book_info.get('amazon_rating', '')
    amazon_rating_count = original_book_info.get('amazon_rating_count', '')
    goodreads_rating = original_book_info.get('goodreads_rating', '')
    goodreads_rating_count = original_book_info.get('goodreads_rating_count', '')
    
    ratings = []
    if amazon_rating:
        if amazon_rating_count:
            ratings.append(f"Amazon: {amazon_rating} ({amazon_rating_count} ratings)")
        else:
            ratings.append(f"Amazon: {amazon_rating}")
    
    if goodreads_rating:
        if goodreads_rating_count:
            ratings.append(f"Goodreads: {goodreads_rating} ({goodreads_rating_count} ratings)")
        else:
            ratings.append(f"Goodreads: {goodreads_rating}")
    
    feishu_data["评分"] = " | ".join(ratings) if ratings else ""
    
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
    soup = BeautifulSoup(html_content, 'html.parser')
    book_info = {}
    
    # Optional ISBN override from filename or command line argument
    url_isbn_override = None
    if file_name:
        # Try to extract ISBN from filename or provided URL
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
            book_info['作者简介'] = '\n'.join([p.text.strip() for p in paragraphs])
    
    # Extract book description
    description_element = soup.select_one('#bookDescription_feature_div .a-expander-content')
    if description_element:
        book_info['内容简介'] = description_element.text.strip()
    else:
        description_element = soup.select_one('#productDescription')
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
        url_isbn = "1847941834"  # Fallback to example ISBN
    
    # Ensure the ISBN is complete
    if len(url_isbn) < 10:
        url_isbn = "1847941834"
    
    # Construct Amazon URL with correct domain
    base_url = "https://www.amazon.co.uk"  # 确保始终使用UK域名
    if '书名' in book_info:
        url_title = re.sub(r'[^\w\s-]', '', book_info['书名'])
        url_title = re.sub(r'\s+', '-', url_title.strip())
        book_url = f"{base_url}/{url_title}/dp/{url_isbn}"
        # 确保使用正确的域名
        for domain in ['amazon.com', 'amazon.co.jp']:
            if domain in book_url:
                book_url = book_url.replace(domain, "www.amazon.co.uk")
        book_info['书本页面'] = book_url
    else:
        book_url = f"{base_url}/dp/{url_isbn}"
        # 确保使用正确的域名
        for domain in ['amazon.com', 'amazon.co.jp']:
            if domain in book_url:
                book_url = book_url.replace(domain, "www.amazon.co.uk")
        book_info['书本页面'] = book_url
    
    # Extract publisher and publication date
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
    
    # 如果上面的选择器都没有找到，尝试更多通用的方法
    if not publisher_found:
        # 尝试从 Detail Bullets 中提取
        bullet_items = soup.select('#detailBullets_feature_div li, #detail-bullets li, #detailBulletsWrapper_feature_div .a-list-item')
        for item in bullet_items:
            item_text = item.text.lower()
            if 'publisher' in item_text:
                # 提取冒号或分隔符后面的文本
                match = re.search(r'publisher\s*(?::|：|\|)\s*([^;]+)', item_text, re.IGNORECASE)
                if match:
                    publisher_text = match.group(1).strip()
                    # 进一步清理日期信息
                    publisher_text = re.sub(r'(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{2}/\d{2}/\d{4})', '', publisher_text)
                    publisher_text = publisher_text.strip('; :.,')
                    
                    if publisher_text:
                        book_info['出版社'] = publisher_text
                        print(f"Found publisher from detail bullets: {book_info['出版社']}")
                        publisher_found = True
                        break
    
    # 如果还没找到，尝试直接从产品详情表格中提取
    if not publisher_found:
        product_details = soup.select('#prodDetails .prodDetTable tr, #productDetailsTable .content tr')
        for detail in product_details:
            detail_text = detail.text.lower()
            if 'publisher' in detail_text:
                # 尝试只提取值部分
                if detail.select_one('td'):
                    publisher_text = detail.select_one('td').text.strip()
                    # 清理日期信息
                    publisher_text = re.sub(r'(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{2}/\d{2}/\d{4})', '', publisher_text)
                    publisher_text = publisher_text.strip('; :.,')
                    
                    if publisher_text:
                        book_info['出版社'] = publisher_text
                        print(f"Found publisher from product details: {book_info['出版社']}")
                        publisher_found = True
                        break
    
    # 如果上面的方法都没有找到，最后尝试使用备用方法
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
    
    # Extract related books
    related_books = []
    related_sections = [
        'Customers who viewed this item also viewed', 
        'Customers who bought this item also bought',
        'Products related to this item',
        'Compare with similar items'
    ]
    
    # Extract related books logic
    for section_text in related_sections:
        related_heading = soup.find('h2', string=lambda s: s and section_text in s)
        if related_heading:
            carousel = related_heading.find_next('div', class_='a-carousel-viewport')
            if carousel:
                carousel_items = carousel.select('li.a-carousel-card')
                for item in carousel_items[:8]:
                    a_tag = item.select_one('a.a-link-normal')
                    if a_tag:
                        title_element = item.select_one('._cDEzb_p13n-sc-css-line-clamp-3_g3dy1, ._cDEzb_p13n-sc-css-line-clamp-4_2q2cc, .a-size-base-plus')
                        if title_element and title_element.text.strip():
                            title = title_element.text.strip()
                            url = a_tag.get('href')
                            if url:
                                if not url.startswith('http'):
                                    url = "https://www.amazon.co.uk" + url
                                related_book = {"title": title, "url": url}
                                related_books.append(related_book)
    
    # Limit to 8 items
    if related_books:
        book_info['关联图书'] = related_books[:8]
    
    # Extract reviews
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
    if '书名' in book_info:
        url_title = re.sub(r'[^\w\s-]', '', book_info['书名'])
        url_title = re.sub(r'\s+', '-', url_title.strip())
        book_url = f"{base_url}/{url_title}/dp/{url_isbn}"
        # 确保使用正确的域名
        for domain in ['amazon.com', 'amazon.co.uk']:
            if domain in book_url:
                book_url = book_url.replace(domain, "www.amazon.co.jp")
        book_info['书本页面'] = book_url
    else:
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
    first_carousel = soup.select_one('ol.a-carousel')
    if first_carousel:
        carousel_items = first_carousel.select('li.a-carousel-card')[:10]
        for item in carousel_items:
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
        
        if related_books:
            print(f"从页面第一个轮播中找到 {len(related_books)} 本相关书籍")
            book_info['关联图书'] = related_books
    
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
    """从HTML文件中提取图书信息，支持多区域"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 直接使用html_content和domain参数调用extract_book_info_from_html
        # domain参数会优先用于确定区域
        book_info = extract_book_info_from_html(html_content, file_name=file_path, domain=domain)
        
        return book_info
        
    except Exception as e:
        print(f"Error extracting book info from file {file_path}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        # 返回一个默认的空数据结构，而不是None
        return {
            "title": "",
            "书名": "",
            "标题": "",
            "作者": "",
            "author": "",
            "publisher": "",
            "出版社": "",
            "publication_date": "",
            "出版时间": "",
            "ISBN": "",
            "isbn": "",
            "description": "",
            "内容简介": "",
            "author_bio": "",
            "作者简介": "",
            "url": "",
            "书本页面": "",
            "region": region or "unknown"
        }

def send_to_feishu(data, webhook_url):
    """
    Send data to Feishu webhook.
    
    Args:
        data (dict): Data to send to Feishu
        webhook_url (str): Feishu webhook URL
        
    Returns:
        bool: True if sending was successful, False otherwise
    """
    try:
        # 确保data是dict类型
        if not isinstance(data, dict):
            print(f"数据格式错误，期望dict类型，实际是{type(data)}")
            return False
        
        # 确保data包含必要的字段
        expected_keys = ["书名", "书本页面", "作者", "作者页面", "作者简介", "内容简介", 
                          "出版时间", "出版社", "ISBN", "封面", "关联图书", "评分", "读者评论"]
        
        for key in expected_keys:
            if key not in data:
                data[key] = ""  # 添加缺失的字段，确保格式完整
        
        # 确保所有值都是字符串类型
        for key in data:
            if not isinstance(data[key], str):
                data[key] = str(data[key])
        
        # 打印请求信息，便于调试
        print("发送请求到飞书webhook...")
        print(f"webhook URL: {webhook_url}")
        print(f"请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        # 发送数据到飞书webhook
        headers = {'Content-Type': 'application/json'}
        response = requests.post(webhook_url, json=data, headers=headers, timeout=10)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            print("成功发送数据到飞书webhook")
            return True
        else:
            print(f"发送数据到飞书webhook失败: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"发送数据到飞书webhook时发生异常: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """Main function to handle command-line arguments."""
    parser = argparse.ArgumentParser(description='Extract book information from Amazon product page and send to Feishu webhook.')
    parser.add_argument('html_file', help='Path to the HTML file or URL of the Amazon product page')
    parser.add_argument('--webhook', help='Feishu webhook URL')
    parser.add_argument('--output', help='Output JSON file path')
    parser.add_argument('--domain', help='Amazon domain (e.g., amazon.com, amazon.co.uk, amazon.co.jp)')
    
    args = parser.parse_args()
    
    # Check if input is a URL or a file
    if args.html_file.startswith('http'):
        # Extract from URL
        book_info = extract_from_url(args.html_file, domain=args.domain)
    else:
        # Extract from file
        book_info = extract_from_file(args.html_file, domain=args.domain)
    
    # Save to JSON file if output path is provided
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(book_info, f, ensure_ascii=False, indent=2)
        print(f"书籍信息已保存到 {args.output}")
    
    # Send to Feishu webhook if URL is provided
    if args.webhook:
        success = send_to_feishu(book_info, args.webhook)
        if success:
            print("成功发送数据到飞书webhook")
        else:
            print(f"发送数据到飞书webhook失败")

if __name__ == "__main__":
    main()
