#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
from bs4 import BeautifulSoup
import sys
import datetime

def extract_jp_book_info(html_content, file_name=None):
    """Extract book information from Amazon Japan HTML content"""
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
    author_element = soup.select_one('#bylineInfo .author a, #bylineInfo .contributorNameID')
    if author_element:
        book_info['作者'] = author_element.text.strip()
        author_href = author_element.get('href')
        if author_href:
            if author_href.startswith('http'):
                book_info['作者页面'] = author_href
            else:
                book_info['作者页面'] = "https://www.amazon.co.jp" + author_href
        else:
            book_info['作者页面'] = ""
    
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
        if len(sys.argv) > 1:
            file_name = sys.argv[1]
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
        # 不再截取ISBN-13的后10位，而是寻找ISBN-10或保留完整ISBN
        if url_isbn.startswith('978') and len(url_isbn) >= 13:
            # 尝试从HTML中查找ISBN-10
            isbn10_from_html = soup.select_one('#rpi-attribute-book_details-isbn10 .rpi-attribute-value, tr:has(th:contains("ISBN-10")) td, tr:has(th:contains("ISBN")) td')
            if isbn10_from_html and len(isbn10_from_html.text.strip()) == 10:
                url_isbn = isbn10_from_html.text.strip()
    else:
        url_isbn = "4478106789"  # Fallback to example ISBN
    
    # Ensure the ISBN is complete and correct
    if len(url_isbn) < 10:
        url_isbn = "4478106789"
    
    # 优先从URL或文件名中提取完整的ISBN
    if file_name:
        isbn_direct_match = None
        # 首先尝试直接匹配dp/后的ISBN
        if "dp/" in file_name:
            isbn_from_url = re.search(r'dp/(\d{10,13})(/|$|\?)', file_name)
            if isbn_from_url:
                isbn_direct_match = isbn_from_url.group(1)
        
        # 如果找到了直接匹配，使用它
        if isbn_direct_match:
            url_isbn = isbn_direct_match
    
    # 始终使用最简单的格式，避免复杂URL导致的问题
    book_info['书本页面'] = f"https://www.amazon.co.jp/dp/{url_isbn}"
    
    # 额外保存一个ISBN-10字段，用于URL和参考
    if url_isbn and len(url_isbn) == 10:
        book_info['ISBN-10'] = url_isbn
    
    # Extract publisher and publication date
    publisher_element = soup.select_one('#rpi-attribute-book_details-publisher .rpi-attribute-value, tr:has(th:contains("出版社")) td')
    if publisher_element:
        book_info['出版社'] = publisher_element.text.strip()
    
    pub_date_element = soup.select_one('#rpi-attribute-book_details-publication_date .rpi-attribute-value, tr:has(th:contains("発売日")) td')
    if pub_date_element:
        book_info['出版时间'] = pub_date_element.text.strip()
    else:
        publisher_element = soup.select_one('#productSubtitle')
        if publisher_element:
            subtitle_text = publisher_element.text.strip()
            pub_date_match = re.search(r'(\d+年\d+月\d+日)', subtitle_text)
            if pub_date_match:
                book_info['出版时间'] = pub_date_match.group(1)
    
    # Extract related books
    related_books = []
    
    # 添加调试信息
    print("\n开始提取相关图书...")
    
    # 日语相关商品标题
    jp_related_titles = [
        "この商品に関連する商品",
        "この商品を買った人はこんな商品も買っています",
        "この商品をチェックした人はこんな商品もチェックしています",
        "よく一緒に購入されている商品",
        "この商品を見た後に買っているのは？",
        "Kindle 限定 あわせて読みたい本",
        "類似商品と比較する",
        "おすすめ商品",
        "ページ目次",
        "この本を買った人はこんな本も買っています"
    ]
    
    # 寻找日语相关商品部分 - 使用更宽松的匹配
    related_section = None
    
    # 方法1: 通过h2标题查找
    print("方法1: 通过h2标题查找相关商品部分...")
    for title in jp_related_titles:
        headings = soup.select('h2, h3')
        for heading in headings:
            if title in heading.text:
                print(f"找到相关标题: {heading.text}")
                related_section = heading
                break
        if related_section:
            break
    
    # 如果找到相关商品部分，尝试提取相关书籍
    if related_section:
        print("找到相关商品部分，尝试提取相关书籍...")
        # 寻找最接近标题的轮播容器
        parent_div = related_section.parent
        if parent_div:
            # 尝试找到轮播内容
            carousel = parent_div.select_one('.a-carousel, .a-carousel-container, ul.a-carousel, .a-carousel-viewport')
            if carousel:
                print("找到轮播容器，开始提取书籍...")
                # 从轮播中提取相关书籍
                items = carousel.select('li, .a-carousel-card, div.a-carousel-card')
                print(f"找到 {len(items)} 个潜在的相关商品")
                for item in items[:8]:  # 最多提取8本相关书籍
                    book = {}
                    
                    # 获取书名
                    title_element = item.select_one('img')
                    if title_element and title_element.get('alt'):
                        book['title'] = title_element.get('alt').strip()
                    else:
                        title_element = item.select_one('.p13n-sc-truncate, .a-truncate-cut, .a-size-base')
                        if title_element:
                            book['title'] = title_element.text.strip()
                    
                    # 获取链接
                    link_element = item.select_one('a')
                    if link_element and link_element.get('href'):
                        href = link_element.get('href')
                        if '/dp/' in href or '/product/' in href:
                            # 确保链接是正确格式
                            if href.startswith('/'):
                                book['url'] = f"https://www.amazon.co.jp{href}"
                            elif href.startswith('http'):
                                book['url'] = href
                    
                    # 只添加有标题和链接的书籍
                    if book.get('title') and book.get('url'):
                        print(f"添加相关书籍: {book['title']}")
                        related_books.append(book)
    
    # 方法2: 通过ID直接查找相关产品容器
    if len(related_books) < 2:
        print("\n方法2: 通过ID直接查找相关产品容器...")
        # 尝试从常见的相关产品容器中提取
        common_containers = [
            '#sims-consolidated-2_feature_div',
            '#sims-consolidated-1_feature_div',
            '#purchase-sims-feature',
            '#sims-fbt-container',
            '#similarities_feature_div',
            '.sims-carousel-holder',
            '#sims-consolidated-3_feature_div',
            '#sims-consolidated-4_feature_div',
            '#personalizedBasedOnCartItems_feature_div',
            '#browse_feature_div',
            '#customerAlsoBoughtItems_feature_div'
        ]
        
        for container_id in common_containers:
            if len(related_books) >= 8:
                break
                
            container = soup.select_one(container_id)
            if container:
                print(f"找到容器: {container_id}")
                # 提取所有书籍条目
                items = container.select('li, .a-carousel-card, .a-column, div.zg-grid-general-faceout')
                print(f"在容器中找到 {len(items)} 个潜在的相关商品")
                for item in items[:8 - len(related_books)]:
                    book = {}
                    
                    # 获取书名 - 多种可能的元素
                    title_found = False
                    
                    # 方法1: 从图片alt属性获取
                    title_element = item.select_one('img')
                    if title_element and title_element.get('alt') and len(title_element.get('alt').strip()) > 3:
                        book['title'] = title_element.get('alt').strip()
                        title_found = True
                    
                    # 方法2: 从标题元素获取
                    if not title_found:
                        for title_selector in ['.p13n-sc-truncate', '.a-truncate-cut', '.a-size-base', '.a-link-normal span', '.a-text-normal']:
                            title_element = item.select_one(title_selector)
                            if title_element and title_element.text.strip():
                                book['title'] = title_element.text.strip()
                                title_found = True
                                break
                    
                    # 方法3: 从链接标题获取
                    if not title_found:
                        link_element = item.select_one('a')
                        if link_element and link_element.get('title'):
                            book['title'] = link_element.get('title').strip()
                    
                    # 获取链接 - 确保包含dp/或product/
                    link_element = item.select_one('a')
                    if link_element and link_element.get('href'):
                        href = link_element.get('href')
                        if '/dp/' in href or '/product/' in href or '/gp/product/' in href:
                            # 确保链接是正确格式
                            if href.startswith('/'):
                                book['url'] = f"https://www.amazon.co.jp{href}"
                            elif href.startswith('http'):
                                book['url'] = href
                    
                    # 过滤掉非书籍项目
                    skip_keywords = [
                        'ビデオゲーム', 'DVD', 'ブルーレイ', 'おもちゃ', 'ゲーム', 'アパレル',
                        'ガジェット', 'デバイス', 'アクセサリー', 'バッテリー', 'ケース',
                        'カバー', 'バッグ', 'カード', 'プレー', 'ボードゲーム'
                    ]
                    
                    should_skip = False
                    if book.get('title'):
                        for keyword in skip_keywords:
                            if keyword in book.get('title', ''):
                                should_skip = True
                                break
                    
                    # 只添加非重复的有效书籍
                    if (not should_skip and book.get('title') and book.get('url') and
                            book not in related_books):
                        # 检查是否已存在相同标题的书籍
                        title_exists = False
                        for existing_book in related_books:
                            if existing_book.get('title') == book.get('title'):
                                title_exists = True
                                break
                        
                        if not title_exists:
                            print(f"添加相关书籍: {book['title']}")
                            related_books.append(book)
    
    # 方法3: 使用更通用的选择器查找所有可能的相关商品
    if len(related_books) < 2:
        print("\n方法3: 使用更通用的选择器查找相关商品...")
        # 尝试查找常见的产品容器
        general_containers = [
            '.a-carousel-container',
            '.a-carousel',
            '[data-a-carousel-options]',
            '.acswidget-carousel',
            '.sims-carousel'
        ]
        
        for container_selector in general_containers:
            containers = soup.select(container_selector)
            print(f"找到 {len(containers)} 个通用容器")
            for container in containers:
                if len(related_books) >= 8:
                    break
                
                # 检查容器是否有相关商品标题
                has_related_title = False
                heading = container.find_previous('h2') or container.find_previous('h3')
                if heading:
                    for title in jp_related_titles:
                        if title in heading.text:
                            has_related_title = True
                            print(f"找到相关标题: {heading.text}")
                            break
                
                # 即使没有找到相关标题，也继续查找书籍项目
                items = container.select('li, .a-carousel-card, div[data-asin]')
                print(f"在容器中找到 {len(items)} 个潜在的相关商品")
                for item in items[:8 - len(related_books)]:
                    book = {}
                    
                    # 获取书名
                    title_element = item.select_one('img')
                    if title_element and title_element.get('alt'):
                        book['title'] = title_element.get('alt').strip()
                    else:
                        title_selectors = ['.p13n-sc-truncate', '.a-size-base', '.a-link-normal span', '.a-truncate-cut']
                        for selector in title_selectors:
                            title_element = item.select_one(selector)
                            if title_element and title_element.text.strip():
                                book['title'] = title_element.text.strip()
                                break
                    
                    # 获取链接
                    link_element = item.select_one('a')
                    if link_element and link_element.get('href'):
                        href = link_element.get('href')
                        if '/dp/' in href or '/product/' in href:
                            # 确保链接是正确格式
                            if href.startswith('/'):
                                book['url'] = f"https://www.amazon.co.jp{href}"
                            elif href.startswith('http'):
                                book['url'] = href
                    
                    # 可以从ASIN属性提取商品ID
                    if not book.get('url') and item.get('data-asin'):
                        asin = item.get('data-asin')
                        if asin:
                            book['url'] = f"https://www.amazon.co.jp/dp/{asin}"
                    
                    # 过滤和添加
                    skip_keywords = [
                        'ビデオゲーム', 'DVD', 'ブルーレイ', 'おもちゃ', 'ゲーム', 'アパレル',
                        'ガジェット', 'デバイス', 'アクセサリー', 'バッテリー', 'ケース', 'カバー'
                    ]
                    
                    should_skip = False
                    if book.get('title'):
                        for keyword in skip_keywords:
                            if keyword in book.get('title', ''):
                                should_skip = True
                                break
                    
                    if (not should_skip and book.get('title') and book.get('url') and
                            len(book.get('title', '')) > 3):
                        # 检查重复
                        title_exists = False
                        for existing_book in related_books:
                            if existing_book.get('title') == book.get('title'):
                                title_exists = True
                                break
                        
                        if not title_exists:
                            print(f"添加相关书籍: {book['title']}")
                            related_books.append(book)
    
    print(f"\n总共找到 {len(related_books)} 本相关书籍")
    # 保留最多8本相关书籍
    book_info['关联图书'] = related_books[:8]
    
    # Extract ratings
    rating_value = ""
    rating_count = ""
    
    # 寻找日语格式的评分信息
    rating_element = soup.select_one('#averageCustomerReviews, #acrCustomerReviewText')
    if rating_element:
        # 提取评分值
        rating_value_element = soup.select_one('.a-icon-star, #acrPopover, span.a-icon-alt')
        if rating_value_element:
            # 尝试获取星级评分值
            if rating_value_element.name == 'span' and 'a-icon-alt' in rating_value_element.get('class', []):
                rating_text = rating_value_element.text
                rating_match = re.search(r'([\d\.]+) 5つ星のうち|5つ星のうち ([\d\.]+)|5 つ星のうち ([\d\.]+)', rating_text)
                if rating_match:
                    # 获取找到的第一个非空捕获组
                    for i in range(1, 4):
                        if rating_match.group(i):
                            rating_value = rating_match.group(i)
                            break
            elif 'a-icon-star' in rating_value_element.get('class', []):
                # 从类名提取评分值
                for cls in rating_value_element.get('class', []):
                    star_match = re.search(r'a-star-(\d+)', cls)
                    if star_match:
                        rating_value = star_match.group(1)
                        if rating_value.isdigit() and int(rating_value) <= 5:
                            # 将整数星级转换为带小数的评分
                            rating_value = str(int(rating_value))
                            break
            elif rating_value_element.get('title'):
                # 从标题属性提取评分
                title_text = rating_value_element.get('title')
                rating_match = re.search(r'([\d\.]+) 5つ星のうち|5つ星のうち ([\d\.]+)|5 つ星のうち ([\d\.]+)', title_text)
                if rating_match:
                    for i in range(1, 4):
                        if rating_match.group(i):
                            rating_value = rating_match.group(i)
                            break
        
        # 提取评分计数
        rating_count_element = soup.select_one('#acrCustomerReviewText, #ratings-summary .a-declarative, span[data-hook="acr-review-count"]')
        if rating_count_element:
            count_text = rating_count_element.text.strip()
            # 提取数字部分
            count_match = re.search(r'([\d,]+)', count_text)
            if count_match:
                rating_count = count_match.group(1).replace(',', '')
            elif re.search(r'^\d+$', count_text):
                rating_count = count_text
    
    # 如果上面的方法没有找到评分，尝试其他选择器
    if not rating_value:
        alt_rating_elements = [
            '#detailBulletsWrapper_feature_div .a-section:contains("カスタマーレビュー")',
            '#detailBullets_feature_div .a-section:contains("カスタマーレビュー")',
            '.a-spacing-top-micro .a-size-base:contains("5つ星のうち")'
        ]
        
        for selector in alt_rating_elements:
            element = soup.select_one(selector)
            if element:
                rating_text = element.text
                rating_match = re.search(r'([\d\.]+) 5つ星のうち|5つ星のうち ([\d\.]+)|5 つ星のうち ([\d\.]+)', rating_text)
                if rating_match:
                    for i in range(1, 4):
                        if rating_match.group(i):
                            rating_value = rating_match.group(i)
                            break
                
                # 寻找评分计数
                count_match = re.search(r'([\d,]+)件のグローバル評価', rating_text)
                if count_match:
                    rating_count = count_match.group(1).replace(',', '')
                break
    
    # 设置平均评分
    if rating_value:
        book_info['评分'] = f"Amazon.co.jp: {rating_value} ({rating_count}件の評価)"
    
    # Extract reviews
    reviews = []
    
    # 选择日本亚马逊常用的评论选择器
    review_elements = soup.select('div[data-hook="review"]')
    
    # 如果没有找到评论，尝试其他日本亚马逊的评论容器
    if not review_elements:
        review_elements = soup.select('.customer-review, .review, #customer-reviews-content .review')
    
    # 处理评论，最多提取10个
    for review_element in review_elements[:10]:
        review = {}
        
        # 获取评论者名称
        reviewer_element = review_element.select_one('.a-profile-name')
        if reviewer_element:
            review['reviewer_name'] = reviewer_element.text.strip()
        
        # 获取评分
        rating_element = review_element.select_one('[data-hook="review-star-rating"], .a-icon-star')
        if rating_element:
            rating_text = rating_element.select_one('.a-icon-alt')
            if rating_text:
                # 匹配日语评分格式
                rating_match = re.search(r'([\d\.]+)[ ]?5つ星のうち|5つ星のうち[ ]?([\d\.]+)|5 つ星のうち[ ]?([\d\.]+)', rating_text.text)
                if rating_match:
                    # 获取匹配的评分
                    for i in range(1, 4):
                        if rating_match.group(i):
                            review['rating'] = rating_match.group(i)
                            break
                else:
                    # 如果没有匹配到，尝试从类名提取
                    classes = rating_element.get('class', [])
                    for cls in classes:
                        if 'a-star-' in cls:
                            review['rating'] = cls.replace('a-star-', '')
                            break
        
        # 获取评论标题
        title_element = review_element.select_one('[data-hook="review-title"], .review-title')
        if title_element:
            title_text = title_element.text.strip()
            # 清理标题中的评分前缀
            title_text = re.sub(r'^\d+\.\d+ 5つ星のうち\s*', '', title_text)
            review['title'] = title_text.strip()
        
        # 获取评论日期
        date_element = review_element.select_one('[data-hook="review-date"], .review-date')
        if date_element:
            review['date'] = date_element.text.strip()
        
        # 获取评论内容
        text_element = review_element.select_one('[data-hook="review-body"], .review-text')
        if text_element:
            content_element = text_element.select_one('[data-hook="review-collapsed"], .review-text-content')
            if content_element:
                review['content'] = content_element.text.strip()
            else:
                review['content'] = text_element.text.strip()
        
        # 获取有用投票数
        helpful_element = review_element.select_one('[data-hook="helpful-vote-statement"], .cr-vote-text')
        if helpful_element:
            review['helpful_votes'] = helpful_element.text.strip()
        else:
            review['helpful_votes'] = ""
        
        # 只添加有足够信息的评论
        if review and (review.get('reviewer_name') or review.get('content')):
            reviews.append(review)
    
    # 如果没有找到足够的评论，尝试从其他容器提取
    if len(reviews) < 3:
        # 其他日本亚马逊评论容器
        alt_review_containers = [
            '#cm-cr-dp-review-list > div',
            '#customerReviews .a-section',
            '.reviews-views .review-item'
        ]
        
        for container_selector in alt_review_containers:
            if len(reviews) >= 10:
                break
                
            alt_review_elements = soup.select(container_selector)
            for review_element in alt_review_elements[:10 - len(reviews)]:
                review = {}
                
                # 获取评论者
                reviewer_element = review_element.select_one('.a-profile-name, .review-byline')
                if reviewer_element:
                    review['reviewer_name'] = reviewer_element.text.strip()
                
                # 获取评分
                rating_element = review_element.select_one('.a-icon-star')
                if rating_element:
                    rating_text = rating_element.get('class', [])
                    for cls in rating_text:
                        if 'a-star-' in cls:
                            review['rating'] = cls.replace('a-star-', '')
                            break
                
                # 获取标题
                title_element = review_element.select_one('.review-title')
                if title_element:
                    review['title'] = title_element.text.strip()
                
                # 获取日期
                date_element = review_element.select_one('.review-date')
                if date_element:
                    review['date'] = date_element.text.strip()
                
                # 获取内容
                content_element = review_element.select_one('.review-text, .review-text-content, p')
                if content_element:
                    review['content'] = content_element.text.strip()
                
                # 只添加非重复的有效评论
                if (review.get('reviewer_name') or review.get('content')) and review not in reviews:
                    reviews.append(review)
    
    # 去重
    unique_reviews = []
    seen_content = set()
    
    for review in reviews:
        # 创建唯一标识符
        content_id = ""
        if review.get('content'):
            # 使用内容前50个字符作为ID
            content_id = review['content'][:50]
        elif review.get('title'):
            # 如果没有内容，使用标题
            content_id = review['title']
        else:
            # 如果都没有，使用评论者名称
            content_id = review.get('reviewer_name', '')
        
        if content_id and content_id not in seen_content:
            seen_content.add(content_id)
            unique_reviews.append(review)
    
    # 如果没有找到评论，添加一个系统评论
    if not unique_reviews and rating_value:
        unique_reviews.append({
            "reviewer_name": "システム",
            "rating": rating_value,
            "title": "評価サマリー",
            "date": datetime.datetime.now().strftime('%Y年%m月%d日'),
            "content": f"この本の平均評価は{rating_value}です。詳しいレビューはAmazon.co.jpで確認できます。",
            "system_generated": True
        })
    
    if unique_reviews:
        book_info['读者评论'] = unique_reviews
    
    return book_info

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_jp_extraction.py <html_file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # Read the HTML file
    with open(file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    
    # Extract book information with the filename for potential ISBN override
    book_info = extract_jp_book_info(html_content, file_path)
    
    # Print the extracted information in a readable format
    print(json.dumps(book_info, indent=2, ensure_ascii=False))
    
    # Print a summary of what was extracted
    print("\n抽出サマリー:")
    for key in book_info:
        if key in ['内容简介', '作者简介']:
            if book_info[key]:
                print(f"✓ {key}: {book_info[key][:50]}...")
        elif key in ['关联图书', '读者评论']:
            print(f"✓ {key}: {len(book_info[key])} 件")
        else:
            print(f"✓ {key}: {book_info[key]}")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'amazonbooks', 'json')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a meaningful filename based on ISBN and title
    isbn = book_info.get('ISBN', '').replace('-', '')
    title = book_info.get('书名', '').split(':')[0][:50]
    timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S-%f')[:-3] + 'Z'
    sanitized_title = re.sub(r'[^\w\s]', '_', title)
    # 使用与示例相同的文件名前缀
    output_filename = f"amazon_book_{isbn}_{sanitized_title}_{timestamp}.json"
    
    # Save to file
    output_path = os.path.join(output_dir, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(book_info, f, indent=2, ensure_ascii=False)
    
    print(f"\n保存先: {output_path}")

if __name__ == "__main__":
    main() 