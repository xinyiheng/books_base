#!/usr/bin/env python3
"""
Amazon Book Information Extractor for Feishu
This script extracts book information from Amazon product pages and formats it for Feishu
"""

import os
import sys
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

def extract_book_info_from_html(html_content, base_url="https://www.amazon.com"):
    """
    Extract book information from HTML content
    """
    # Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Detect language and region from base_url
    region = "us"  # Default to US
    language = "en"  # Default to English
    
    if "amazon.co.uk" in base_url:
        region = "uk"
        language = "en"
    elif "amazon.co.jp" in base_url:
        region = "jp"
        language = "ja"
    
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
        filename = os.path.basename(sys.argv[1]) if len(sys.argv) > 1 else ""
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
    
    # Extract ISBN information - add region-specific selectors for different Amazon sites
    isbn_found = False
    
    # Try standard product details section first
    product_details = soup.select('#detailBulletsWrapper_feature_div .a-unordered-list li .a-text-bold, #productDetailsTable .content li b, .detail-bullet-list span.a-text-bold')
    for detail in product_details:
        detail_text = detail.text.strip().lower()
        if 'isbn' in detail_text or 'isbn-13' in detail_text or 'isbn-10' in detail_text:
            # Get the text after the label
            detail_value = detail.find_next_sibling(text=True)
            if not detail_value:  # Try parent's text if sibling not found
                detail_value = detail.parent.text
            
            if detail_value:
                # Extract digits using regex
                isbn_match = re.search(r'(\d[\d-]+\d)', detail_value)
                if isbn_match:
                    original_book_info["isbn"] = isbn_match.group(1).replace('-', '')
                    print(f"Found ISBN: {original_book_info['isbn']}")
                    isbn_found = True
                    break
    
    # Region-specific ISBN extraction if not found yet
    if not isbn_found:
        if region == "jp":
            # Japan-specific selectors for ISBN
            jp_isbn_selectors = [
                '#detail_bullets_id .content li:contains("ISBN")',
                '.detail-bullet:contains("ISBN")',
                '#productDetails tr:contains("ISBN")'
            ]
            
            for selector in jp_isbn_selectors:
                isbn_elements = soup.select(selector)
                for element in isbn_elements:
                    element_text = element.text.strip()
                    isbn_match = re.search(r'(\d[\d-]+\d)', element_text)
                    if isbn_match:
                        original_book_info["isbn"] = isbn_match.group(1).replace('-', '')
                        print(f"Found ISBN (JP-specific): {original_book_info['isbn']}")
                        isbn_found = True
                        break
                if isbn_found:
                    break
    
    # Extract publication date and publisher with region-specific handling
    pub_date_found = False
    publisher_found = False
    
    # Try to extract from standard product details
    for detail in product_details:
        detail_text = detail.text.strip().lower()
        
        # Check for publication date
        if ('publication date' in detail_text or 'published' in detail_text or 
            'release date' in detail_text or '出版日' in detail_text or 
            'publisher' in detail_text or '出版社' in detail_text):
            
            # Get the text after the label
            detail_value = detail.find_next_sibling(text=True)
            if not detail_value:  # Try parent's text if sibling not found
                detail_value = detail.parent.text
            
            if detail_value:
                # Handle publication date
                if ('publication date' in detail_text or 'published' in detail_text or 
                    'release date' in detail_text or '出版日' in detail_text) and not pub_date_found:
                    # Extract the date part
                    date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},\s+\d{4}|\d{4}/\d{1,2}/\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日)', detail_value)
                    if date_match:
                        original_book_info["publication_date"] = date_match.group(1)
                        print(f"Found publication date: {original_book_info['publication_date']}")
                        pub_date_found = True
                
                # Handle publisher
                if ('publisher' in detail_text or '出版社' in detail_text) and not publisher_found:
                    # Try to extract publisher name
                    publisher_text = detail_value.replace(detail.text, '').strip()
                    if publisher_text:
                        # Clean up the publisher text
                        publisher_match = re.search(r'([^;:()]+)', publisher_text)
                        if publisher_match:
                            original_book_info["publisher"] = publisher_match.group(1).strip()
                            print(f"Found publisher: {original_book_info['publisher']}")
                            publisher_found = True

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
    """
    Convert the extracted book info to the format required by Feishu webhook.
    """
    # Handle related books
    related_books_simple = []
    if original_book_info["related_books"]:
        for book in original_book_info["related_books"]:
            book_text = book["title"]
            if book["author"]:
                book_text += f" - {book['author']}"
            related_books_simple.append(book_text)
    
    # Create the Feishu data structure
    feishu_data = {
        "title": original_book_info["title"],
        "作者": original_book_info["author"],
        "作者简介": original_book_info["author_bio"],
        "内容简介": original_book_info["description"],
        "出版时间": original_book_info["publication_date"],
        "出版社": original_book_info["publisher"],
        "ISBN": original_book_info["isbn"],
        "封面": original_book_info["cover_image_url"],
        "关联图书": related_books_simple,  # 使用简单的文本列表
        "评分": "",
        "读者评论": original_book_info["reviews"],
        "地区": original_book_info["region"],  # Add region information
        "语言": original_book_info["language"]  # Add language information
    }
    
    # Format ratings
    if original_book_info["amazon_rating"]:
        rating_text = f"Amazon: {original_book_info['amazon_rating']}"
        if original_book_info["amazon_rating_count"]:
            rating_text += f" ({original_book_info['amazon_rating_count']})"
        feishu_data["评分"] = rating_text
    
    # Print related books information for debugging
    print("\n关联图书信息:")
    for book in feishu_data["关联图书"]:
        print(book)
    
    return feishu_data

def extract_from_url(url):
    """
    Extract book information from an Amazon product URL
    """
    try:
        # Detect the Amazon domain
        base_url = detect_amazon_domain(url)
        print(f"Detected Amazon domain: {base_url}")
        
        # Send a request to the URL with a delay to avoid being blocked
        print(f"Sending request to {url}...")
        time.sleep(random.uniform(1, 3))  # Add a random delay
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        # Check if the request was successful
        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            return {'error': f'Failed to fetch page: Status code {response.status_code}'}
        
        # Save the HTML content to a file for debugging
        with open('amazon_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"Saved HTML content to amazon_page.html")
        
        # Extract book info from HTML content
        return convert_to_feishu_format(extract_book_info_from_html(response.text, base_url=base_url))
    
    except Exception as e:
        print(f"Error extracting book info: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return {'error': f'Failed to extract book information: {str(e)}'}

def extract_from_file(file_path):
    """
    Extract book information from a local HTML file.
    
    Args:
        file_path (str): Path to the HTML file.
        
    Returns:
        dict: Extracted book information.
    """
    try:
        print(f"Reading HTML file: {file_path}")
        
        # Handle file path special characters
        # 1. Remove possible quotes
        clean_path = file_path.strip('"\'')
        
        # 2. Check if file exists, if not, try to find file using glob
        if not os.path.exists(clean_path):
            print(f"File not found at path: {clean_path}")
            print("Trying to find file using pattern matching...")
            
            # Get directory and base file name
            dir_path = os.path.dirname(clean_path) or '.'
            base_name = os.path.basename(clean_path)
            
            # Use glob to find matching files
            import glob
            matching_files = glob.glob(os.path.join(dir_path, "*"))
            
            # Find the most similar file name
            best_match = None
            best_similarity = 0
            
            for file in matching_files:
                if os.path.isfile(file):
                    # Use simple similarity matching (can be replaced with a more complex algorithm)
                    file_base = os.path.basename(file)
                    # Calculate the percentage of identical characters in the two file names
                    similarity = sum(c1 == c2 for c1, c2 in zip(file_base.lower(), base_name.lower())) / max(len(file_base), len(base_name))
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = file
            
            if best_match and best_similarity > 0.7:  # Set a similarity threshold
                print(f"Found matching file: {best_match}")
                clean_path = best_match
            else:
                raise FileNotFoundError(f"Could not find a matching file for: {file_path}")
        
        # Try to extract author information from the file name
        author_from_filename = None
        filename = os.path.basename(clean_path)
        
        # Use regular expression to find author pattern
        author_match = re.search(r'_\s*([A-Z][a-z]+),\s*([A-Z][a-z]+)_', filename)
        if author_match:
            last_name = author_match.group(1)
            first_name = author_match.group(2)
            author_from_filename = f"{first_name} {last_name}"
            print(f"Extracted author from filename: {author_from_filename}")
        
        # Read HTML content, try multiple encodings
        html_content = None
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(clean_path, 'r', encoding=encoding) as f:
                    html_content = f.read()
                print(f"Successfully read file with encoding: {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if html_content is None:
            # If all encodings fail, read in binary mode and try to detect encoding
            import chardet
            with open(clean_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                html_content = raw_data.decode(encoding)
                print(f"Detected encoding: {encoding}")
        
        # Extract book info from HTML content
        book_info = extract_book_info_from_html(html_content)
        
        # If author wasn't found but we extracted it from filename, use that
        if not book_info["author"] and author_from_filename:
            book_info["author"] = author_from_filename
            print(f"Using author from filename: {author_from_filename}")
        
        return convert_to_feishu_format(book_info)
    
    except Exception as e:
        print(f"Error extracting book info from file: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return {'error': f'Failed to extract book information from file: {str(e)}'}

def send_to_feishu(data, webhook_url):
    """Send data to Feishu webhook."""
    headers = {'Content-Type': 'application/json'}
    response = requests.post(webhook_url, json=data, headers=headers)
    return response

def main():
    """Main function to handle command-line arguments."""
    parser = argparse.ArgumentParser(description='Extract book information from Amazon product page and send to Feishu webhook.')
    parser.add_argument('html_file', help='Path to the HTML file or URL of the Amazon product page')
    parser.add_argument('--webhook', help='Feishu webhook URL')
    parser.add_argument('--output', help='Output JSON file path')
    
    args = parser.parse_args()
    
    # Check if input is a URL or a file
    if args.html_file.startswith('http'):
        # Extract from URL
        book_info = extract_from_url(args.html_file)
    else:
        # Extract from file
        book_info = extract_from_file(args.html_file)
    
    # Save to JSON file if output path is provided
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(book_info, f, ensure_ascii=False, indent=2)
        print(f"Book information saved to {args.output}")
    
    # Send to Feishu webhook if URL is provided
    if args.webhook:
        response = send_to_feishu(book_info, args.webhook)
        if response.status_code == 200:
            print("Successfully sent data to Feishu webhook")
        else:
            print(f"Failed to send data to Feishu webhook: {response.status_code} {response.text}")

if __name__ == "__main__":
    main()
