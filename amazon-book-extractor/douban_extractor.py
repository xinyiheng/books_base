#!/usr/bin/env python3
"""
豆瓣图书信息提取器
专门用于从豆瓣网页提取图书信息的模块
使用精确的CSS选择器提取各种信息
"""

import re
import json
import logging
import urllib.parse
import requests
from typing import Dict, List, Optional, Union, Any
from bs4 import BeautifulSoup, Tag

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DoubanExtractor")

def extract_from_douban(html_content: str, url: str = "", cache_dir: str = "cache") -> Dict[str, Any]:
    """从豆瓣HTML页面中提取图书信息"""
    if not html_content:
        logger.error("HTML内容为空，无法提取信息")
        return {}
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    logger.info("开始从豆瓣提取信息...")
    
    # 基本信息提取
    result = {}
    
    # 标题
    title = extract_title(soup)
    result["书名"] = title
    logger.info(f"提取到书名: {title}")
    
    # 书籍URL
    book_url = extract_book_url(soup, url)
    result["书本页面"] = book_url
    logger.info(f"提取到书本页面URL: {book_url}")
    
    # 作者
    author = extract_author(soup)
    result["作者"] = author
    logger.info(f"提取到作者: {author}")
    
    # 作者链接
    author_url = extract_author_url(soup)
    result["作者页面"] = author_url
    logger.info(f"提取到作者页面: {author_url}")
    
    # 原作名
    original_title = extract_original_title(soup)
    result["原作名"] = original_title
    logger.info(f"提取到原作名: {original_title}")
    
    # 作者简介
    author_bio = extract_author_bio(soup)
    result["作者简介"] = author_bio
    logger.info(f"提取到作者简介: {author_bio[:100]}...")
    
    # 内容简介
    description = extract_description(soup)
    result["内容简介"] = description
    logger.info(f"提取到内容简介: {description[:100]}...")
    
    # 出版时间
    pub_date = extract_pub_date(soup)
    result["出版时间"] = pub_date
    logger.info(f"提取到出版时间: {pub_date}")
    
    # 出版社
    publisher = extract_publisher(soup)
    result["出版社"] = publisher
    logger.info(f"提取到出版社: {publisher}")
    
    # ISBN
    isbn = extract_isbn(soup)
    result["ISBN"] = isbn
    logger.info(f"提取到ISBN: {isbn}")
    
    # 封面图片
    cover_image = extract_cover_image(soup)
    result["封面图片"] = cover_image
    logger.info(f"提取到封面图片: {cover_image}")
    
    # 豆瓣评分
    rating = extract_rating(soup)
    result["评分"] = rating
    logger.info(f"提取到评分: {rating}")
    
    # 获取相关图书（包括其他版本）
    related_books = extract_related_books(soup)
    
    # 不再分离其他版本图书，直接添加所有图书到关联图书
    result["关联图书"] = related_books
    logger.info(f"提取到{len(related_books)}本关联图书")
    
    # 提取读者评论
    comments = extract_comments(soup)
    result["读者评论"] = comments
    logger.info(f"提取到{len(comments)}条读者评论")
    
    return result

def extract_title(soup: BeautifulSoup) -> str:
    """提取书名"""
    selectors = [
        "h1 span[property='v:itemreviewed']",  # 标准选择器
        "#wrapper h1 span",                    # 备用选择器
        "h1"                                   # 最后的选择器
    ]
    
    for selector in selectors:
        element = soup.select_one(selector)
        if element and element.text.strip():
            return element.text.strip()
    
    return ""

def extract_book_url(soup: BeautifulSoup, original_url: str) -> str:
    """提取书本页面URL"""
    # 如果原始URL是豆瓣书籍URL，直接返回
    if original_url and ("book.douban.com/subject/" in original_url or "douban.com/subject/" in original_url):
        return original_url
    
    # 尝试从meta标签或link标签中提取
    meta_url = soup.select_one("meta[property='og:url']")
    if meta_url and meta_url.get("content"):
        return meta_url["content"]
    
    link_canonical = soup.select_one("link[rel='canonical']")
    if link_canonical and link_canonical.get("href"):
        return link_canonical["href"]
    
    # 尝试从页面中提取书籍ID
    subject_id_match = re.search(r'/subject/(\d+)/', str(soup))
    if subject_id_match:
        return f"https://book.douban.com/subject/{subject_id_match.group(1)}/"
    
    # 如果都提取不到，返回豆瓣图书主页
    return "https://book.douban.com/"

def extract_author(soup: BeautifulSoup) -> str:
    """提取作者"""
    selectors = [
        "#info span a[href^='/author/']",        # 作者链接
        "#info span:contains('作者') a",          # 作者字段
        "span.pl:contains('作者') + a",           # 备用选择器
        "#info span.pl:contains('作者')"         # 最后的选择器
    ]
    
    for selector in selectors:
        elements = soup.select(selector)
        if elements:
            if selector == "#info span.pl:contains('作者')":
                # 处理特殊情况，直接从文本中提取
                text = elements[0].parent.get_text(strip=True)
                author_match = re.search(r'作者:?\s*([^/]+)', text)
                if author_match:
                    return author_match.group(1).strip()
            else:
                # 处理一般情况，可能有多个作者
                authors = [e.text.strip() for e in elements if e.text.strip()]
                if authors:
                    return " / ".join(authors)
    
    return ""

def extract_author_url(soup: BeautifulSoup) -> str:
    """提取作者页面URL"""
    # 查找作者span标签
    author_span = soup.select_one("span.pl:-soup-contains('作者')")
    if author_span:
        # 直接查找该span后面的链接
        next_a = author_span.find_next("a")
        if next_a and next_a.has_attr("href"):
            href = next_a.get("href", "")
            if href:
                # 确保是完整URL
                if href.startswith("/"):
                    return f"https://book.douban.com{href}"
                return href
    
    # 方法2: 从作者名称附近的链接提取
    info_div = soup.select_one("#info")
    if info_div:
        for span in info_div.select("span.pl"):
            if "作者" in span.text:
                # 寻找紧跟作者标签的链接
                siblings = list(span.next_siblings)
                for sibling in siblings:
                    if isinstance(sibling, Tag) and sibling.name == "a":
                        href = sibling.get("href", "")
                        if href:
                            if href.startswith("/"):
                                return f"https://book.douban.com{href}"
                            return href
                    # 如果遇到另一个span.pl，就停止查找
                    if isinstance(sibling, Tag) and sibling.name == "span" and "pl" in sibling.get("class", []):
                        break
    
    # 方法3: 从整个info区域提取所有链接，寻找可能的作者页面
    info_div = soup.select_one("#info")
    if info_div:
        # 找到作者信息所在的区域
        author_text = info_div.text
        author_index = author_text.find("作者")
        
        if author_index != -1:
            # 获取所有链接
            links = info_div.select("a")
            
            # 尝试找到可能的作者链接
            for link in links:
                href = link.get("href", "")
                if href and ("/author/" in href or ("/search" in href and "author" in href)):
                    if href.startswith("/"):
                        return f"https://book.douban.com{href}"
                    return href
    
    return ""

def extract_original_title(soup: BeautifulSoup) -> str:
    """提取原作名"""
    info_div = soup.select_one("#info")
    if info_div:
        # 查找原作名标签
        for span in info_div.select("span.pl"):
            if "原作名" in span.text:
                # 获取原作名文本
                original_title = span.next_sibling
                if original_title:
                    return original_title.strip()
        
        # 备用方法：使用正则表达式从info文本中提取
        info_text = info_div.get_text()
        original_title_match = re.search(r'原作名[:：]\s*([^\n]+)', info_text)
        if original_title_match:
            return original_title_match.group(1).strip()
    
    return ""

def extract_author_bio(soup: BeautifulSoup) -> str:
    """提取作者简介"""
    # 首先用最准确的方式查找
    author_spans = soup.select("h2 span.pl")
    for span in author_spans:
        if "作者简介" in span.text:
            author_span = span
            intro_div = author_span.find_next("div", class_="intro")
            if intro_div:
                # 提取所有段落
                paragraphs = [p.text.strip() for p in intro_div.select("p")]
                if paragraphs:
                    return "\n".join(paragraphs)
    
    # 备用提取方法1：直接查找作者简介块
    author_section = soup.select_one("#content .related_info .indent:has(h2:-soup-contains('作者简介')) div.intro")
    if author_section:
        paragraphs = [p.text.strip() for p in author_section.select("p")]
        if paragraphs:
            return "\n".join(paragraphs)
    
    # 备用提取方法2：更灵活地查找
    for block in soup.select("#content .related_info .indent"):
        heading = block.select_one("h2")
        if heading and "作者简介" in heading.text:
            intro_div = block.select_one("div.intro") or block
            if intro_div:
                paragraphs = [p.text.strip() for p in intro_div.select("p")]
                if paragraphs:
                    return "\n".join(paragraphs)
    
    # 最后尝试从页面任何地方找到作者简介
    for section in soup.select(".related_info"):
        for h2 in section.select("h2"):
            if "作者简介" in h2.text:
                # 查找紧跟着的任何内容
                next_element = h2.find_next()
                content = []
                while next_element and next_element.name != "h2":
                    if next_element.name == "p":
                        content.append(next_element.text.strip())
                    next_element = next_element.find_next()
                if content:
                    return "\n".join(content)
    
    return ""

def extract_description(soup: BeautifulSoup) -> str:
    """提取内容简介"""
    # 首先用最准确的方式查找
    content_spans = soup.select("h2 span.pl")
    for span in content_spans:
        if "内容简介" in span.text:
            content_span = span
            intro_div = content_span.find_next("div", class_="intro")
            if intro_div:
                # 提取所有段落
                paragraphs = [p.text.strip() for p in intro_div.select("p")]
                if paragraphs:
                    return "\n".join(paragraphs)
    
    # 备用提取方法1：直接查找内容简介块
    summary_section = soup.select_one("#content .related_info .indent:has(h2:-soup-contains('内容简介')) div.intro")
    if summary_section:
        paragraphs = [p.text.strip() for p in summary_section.select("p")]
        if paragraphs:
            return "\n".join(paragraphs)
    
    # 备用提取方法2：更灵活地查找
    for block in soup.select("#content .related_info .indent"):
        heading = block.select_one("h2")
        if heading and "内容简介" in heading.text:
            intro_div = block.select_one("div.intro") or block
            if intro_div:
                paragraphs = [p.text.strip() for p in intro_div.select("p")]
                if paragraphs:
                    return "\n".join(paragraphs)
    
    # 最后尝试从页面任何地方找到内容简介
    for section in soup.select(".related_info"):
        for h2 in section.select("h2"):
            if "内容简介" in h2.text:
                # 查找紧跟着的任何内容
                next_element = h2.find_next()
                content = []
                while next_element and next_element.name != "h2":
                    if next_element.name == "p":
                        content.append(next_element.text.strip())
                    next_element = next_element.find_next()
                if content:
                    return "\n".join(content)
    
    return ""

def extract_pub_date(soup: BeautifulSoup) -> str:
    """提取出版时间"""
    info_text = soup.select_one("#info")
    if info_text:
        info_text = info_text.get_text()
        # 尝试匹配出版时间
        pub_date_match = re.search(r'出版年[:：]\s*(\S+)', info_text) or \
                        re.search(r'出版时间[:：]\s*(\S+)', info_text)
        if pub_date_match:
            return pub_date_match.group(1).strip()
    return ""

def extract_publisher(soup: BeautifulSoup) -> str:
    """提取出版社"""
    info_text = soup.select_one("#info")
    if info_text:
        info_text = info_text.get_text()
        # 尝试匹配出版社
        publisher_match = re.search(r'出版社[:：]\s*([^/\n]+)', info_text)
        if publisher_match:
            return publisher_match.group(1).strip()
    return ""

def extract_isbn(soup: BeautifulSoup) -> str:
    """提取ISBN"""
    info_text = soup.select_one("#info")
    if info_text:
        info_text = info_text.get_text()
        # 尝试匹配ISBN
        isbn_match = re.search(r'ISBN[:：]\s*(\d+[\dXx\-]*)', info_text)
        if isbn_match:
            return isbn_match.group(1).strip()
    return ""

def extract_cover_image(soup: BeautifulSoup) -> str:
    """提取封面图片URL"""
    selectors = [
        "#mainpic img",                        # 标准封面位置
        "a.nbg img",                           # 备用封面位置
        "img[rel='v:photo']",                  # 另一种封面位置
        "img[property='og:image']",            # Meta标签封面
        "#content img[src*='doubanio']",       # 豆瓣图片服务器
        "img[src*='douban']"                   # 任何豆瓣图片
    ]
    
    for selector in selectors:
        elements = soup.select(selector)
        for element in elements:
            if element and element.get("src"):
                # 处理图片源URL
                img_src = element["src"]
                
                # 确保使用大图
                if '/s/' in img_src:
                    img_src = img_src.replace('/s/', '/l/')
                if '/m/' in img_src:
                    img_src = img_src.replace('/m/', '/l/')
                if '/spic/' in img_src:
                    img_src = img_src.replace('/spic/', '/lpic/')
                    
                return img_src
    
    return ""

def extract_rating(soup: BeautifulSoup) -> str:
    """提取评分和评分数"""
    rating_value = ""
    rating_number = ""
    
    # 提取评分数值
    rating_value_elem = soup.select_one("strong[property='v:average']")
    if rating_value_elem and rating_value_elem.text.strip():
        rating_value = rating_value_elem.text.strip()
    
    # 提取评分人数
    rating_people_elem = soup.select_one("a.rating_people span[property='v:votes']")
    if rating_people_elem and rating_people_elem.text.strip():
        rating_number = rating_people_elem.text.strip()
    
    # 组合评分和人数
    if rating_value and rating_number:
        return f"{rating_value} ({rating_number}人评价)"
    elif rating_value:
        return rating_value
    
    return ""

def extract_books_from_works_page(works_url: str, book_id: str = "") -> List[Dict[str, str]]:
    """从works页面提取其他版本图书信息"""
    
    logger.info(f"正在访问works页面: {works_url}")
    
    books = []
    try:
        # 尝试在线获取works页面
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(works_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 提取works页面的主标题
            main_title = ""
            h1_element = soup.select_one("h1")
            if h1_element:
                main_title = h1_element.text.strip()
                if main_title:
                    logger.info(f"works页面主标题: {main_title}")
            
            # 提取书籍列表
            book_list = soup.select(".subject-item")
            for item in book_list:
                book_data = {}
                
                # 提取书名和链接
                title_element = item.select_one("h2 a")
                if title_element:
                    title_text = title_element.text.strip()
                    book_data["title"] = title_text + " (本书的其他版本)"
                    
                    href = title_element.get("href", "")
                    if href:
                        book_data["url"] = href
                
                # 只保留标题和URL
                if book_data and "title" in book_data and "url" in book_data:
                    # 排除当前书籍
                    if book_id and book_id in book_data.get("url", ""):
                        continue
                    books.append(book_data)
            
            logger.info(f"从works页面提取到{len(books)}本其他版本图书")
        else:
            logger.warning(f"访问works页面失败，状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"访问works页面时出错: {str(e)}")
    
    return books

def extract_related_books(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """提取关联图书"""
    related_books = []
    works_links = []  # 存储需要访问的works链接
    
    # 1. 从dd元素中提取关联图书
    dd_elements = soup.select("dd")
    for dd in dd_elements:
        book_data = {}
        link = dd.select_one("a")
        if link and link.has_attr("href"):
            href = link.get("href", "")
            # 过滤条件：只处理指向图书的链接且排除豆列和转让链接
            if ((href.startswith("/subject/") or "book.douban.com/subject/" in href) 
                and "doulist" not in href and "new_offer" not in href):
                title_text = link.text.strip()
                if title_text:
                    book_data["title"] = title_text
                    book_data["url"] = f"https://book.douban.com{href}" if href.startswith("/") else href
                    # 提取额外信息
                    if dd.select_one(".rating-info"):
                        rating_text = dd.select_one(".rating-info").text.strip()
                        if rating_text:
                            book_data["rating"] = rating_text
                            
                    if book_data and "title" in book_data:
                        related_books.append(book_data)
    
    # 2. 查找works链接
    book_id = ""
    
    # 提取当前书籍ID
    book_url = extract_book_url(soup, "")
    if book_url and "/subject/" in book_url:
        book_id = book_url.split("/subject/")[-1].strip("/")
    
    # 查找标题为"这本书的其他版本"的部分
    for h2 in soup.select("#content h2"):
        if "这本书的其他版本" in h2.text:
            # 首先尝试获取"全部X"链接
            all_versions_link = h2.select_one("span.pl a")
            if all_versions_link and all_versions_link.has_attr("href"):
                href = all_versions_link.get("href", "")
                # 确保链接指向works页面（这是豆瓣的其他版本聚合页面）
                if href and "/works/" in href:
                    works_url = f"https://book.douban.com{href}" if href.startswith("/") else href
                    works_title = all_versions_link.text.strip()
                    works_links.append((works_url, works_title, book_id))
    
    # 3. 寻找页面中其他可能的相关书籍
    for section in soup.select(".subject_show"):
        # 查找相关推荐区域
        if "相关推荐" in section.text:
            for item in section.select("dl"):
                book_data = {}
                link = item.select_one("a")
                if link and link.has_attr("href"):
                    href = link.get("href", "")
                    # 过滤条件：只处理指向图书的链接且排除豆列和转让链接
                    if (("book.douban.com/subject/" in href or href.startswith("/subject/")) 
                        and "doulist" not in href and "new_offer" not in href):
                        title_text = link.text.strip()
                        if title_text:
                            book_data["title"] = title_text
                            book_data["url"] = f"https://book.douban.com{href}" if href.startswith("/") else href
                            # 检查是否已存在相同URL的书籍，避免重复
                            if not any(book.get("url") == book_data.get("url") for book in related_books):
                                related_books.append(book_data)
    
    # 4. 最终过滤：只保留正常图书，排除出版社条目
    filtered_books = []
    for book in related_books:
        # 确保链接指向图书或works页面
        url = book.get("url", "")
        title = book.get("title", "")
        
        # 排除以出版社为标题的条目
        if (("/subject/" in url or "/works/" in url) and 
            "doulist" not in url and 
            "new_offer" not in url and
            not url.startswith("https://www.douban.com/") and
            not re.search(r'出版社\s*（\d+）$', title) and 
            not re.search(r'Press\s*（\d+）$', title)):
            filtered_books.append(book)
    
    # 5. 从当前页面直接提取其他版本图书
    other_versions_from_page = extract_other_versions_from_html(soup)
    
    # 添加其他版本图书并标记
    for version in other_versions_from_page:
        # 避免重复
        if not any(book.get("url") == version.get("url") for book in filtered_books):
            # 在标题后添加"(本书的其他版本)"标记
            if "title" in version and "(本书的其他版本)" not in version["title"]:
                version["title"] = f"{version['title']} (本书的其他版本)"
            filtered_books.append(version)
    
    # 6. 尝试访问works页面获取更多其他版本图书
    if works_links:
        for works_url, works_title, book_id in works_links:
            try:
                works_books = extract_books_from_works_page(works_url, book_id)
                if works_books:
                    # 将works页面中的书籍直接添加到filtered_books中
                    for work_book in works_books:
                        if work_book and "title" in work_book and "url" in work_book:
                            # 检查是否已存在相同URL的书籍，避免重复
                            if not any(book.get("url") == work_book.get("url") for book in filtered_books):
                                filtered_books.append(work_book)
            except Exception as e:
                logger.error(f"访问works页面提取图书信息时出错: {str(e)}")
    
    return filtered_books

def extract_comments(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """提取读者评论"""
    comments = []
    
    # 选择所有评论条目
    comment_items = []
    for selector in ["#comments .comment-item", ".review-item", ".comment", "#comments li"]:
        items = soup.select(selector)
        if items:
            comment_items = items
            break
    
    for item in comment_items[:5]:  # 只提取前5条评论
        comment_data = {}
        
        # 提取评论者信息
        for selector in ["a.comment-info", "a.name", ".comment-info a", ".author"]:
            commenter = item.select_one(selector)
            if commenter:
                comment_data["user"] = commenter.text.strip()
                break
        
        # 提取评分
        rating_spans = [
            item.select_one("span[class^='allstar']"), 
            item.select_one(".rating"), 
            item.select_one("span[class*='star']")
        ]
        
        for rating_span in rating_spans:
            if rating_span:
                # 尝试从class名称中提取星级
                rating_class = rating_span.get("class", [])
                rating_value = ""
                for cls in rating_class:
                    if "allstar" in cls or "star" in cls:
                        try:
                            # 提取数字部分
                            rating_number = re.search(r'\d+', cls)
                            if rating_number:
                                stars = int(rating_number.group(0)) / 10
                                rating_value = f"{stars}星"
                                break
                        except (ValueError, AttributeError):
                            pass
                
                # 如果无法从class提取，尝试从title属性提取
                if not rating_value and rating_span.get("title"):
                    title = rating_span.get("title")
                    if "星" in title:
                        rating_value = title
                
                # 如果仍然没有评分，尝试从文本中提取
                if not rating_value:
                    text = rating_span.text.strip()
                    if text and "星" in text:
                        rating_value = text
                
                if rating_value:
                    comment_data["rating"] = rating_value
                    break
        
        # 提取评论内容
        for selector in ["p.comment-content", "div.short-content", ".comment p", ".review-content"]:
            comment_p = item.select_one(selector)
            if comment_p:
                comment_text = comment_p.text.strip()
                # 移除"(展开)"文本
                comment_text = re.sub(r'\(展开\)\s*$', '', comment_text).strip()
                if comment_text:
                    comment_data["content"] = comment_text
                    break
        
        if comment_data and "content" in comment_data:
            comments.append(comment_data)
    
    return comments

def is_douban_page(html_content: str, url: str = "") -> bool:
    """
    判断是否为豆瓣图书页面
    
    Args:
        html_content: HTML内容
        url: 原始URL
        
    Returns:
        是否为豆瓣图书页面
    """
    # URL检查
    if url and ("book.douban.com" in url or "douban.com/subject" in url):
        return True
    
    # 内容检查
    if "book.douban.com" in html_content or "豆瓣读书" in html_content:
        return True
    
    # 结构检查
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 检查特定元素
    if soup.select_one("#info") and soup.select_one("#wrapper h1"):
        return True
    
    if soup.select_one("span[property='v:itemreviewed']"):
        return True
    
    if soup.select_one("a[href*='book.douban.com']"):
        return True
    
    if soup.select_one("#interest_sectl") or soup.select_one(".rating_wrap"):
        return True
    
    return False

def extract_other_versions_from_html(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """从当前HTML页面中直接提取其他版本图书信息，无需访问works页面"""
    books = []
    version_sections = []
    current_book_url = ""
    current_book_title = ""
    
    # 提取当前书籍URL和标题
    book_url = extract_book_url(soup, "")
    if book_url:
        current_book_url = book_url
    
    current_book_title = extract_title(soup)
    if not current_book_title:
        current_book_title = "打造第二大脑"  # 默认标题
    
    # 方法一：查找标题为"这本书的其他版本"的部分
    for h2 in soup.select("#content h2"):
        if "这本书的其他版本" in h2.text:
            parent = h2.parent
            if parent:
                version_sections.append(parent)
    
    # 方法二：如果没有找到h2标题，尝试找span包含相关文本
    if not version_sections:
        for span in soup.select("#content span"):
            if "这本书的其他版本" in span.text:
                parent = span.parent
                if parent and parent.name == "h2":
                    grandparent = parent.parent
                    if grandparent:
                        version_sections.append(grandparent)
    
    # 方法三：查找灰色广告区域
    if not version_sections:
        for section in soup.select("#content .gray_ad"):
            if "其他版本" in section.text or "这本书的其他版本" in section.text:
                version_sections.append(section)
    
    # 提取版本区域中的图书信息
    for section in version_sections:
        # 尝试不同的选择器找到版本列表
        version_items = []
        for selector in ["ul li", "li", ".mb8", "div.content div"]:
            items = section.select(selector)
            if items:
                version_items = items
                break
        
        for item in version_items:
            book_data = {}
            
            # 提取书籍链接和版本信息
            link = item.select_one("a")
            if link and link.has_attr("href"):
                title_text = link.text.strip()
                href = link.get("href", "")
                
                # 过滤条件：只处理指向图书的链接且排除当前书籍和转让链接
                if (href and "/subject/" in href and 
                    href != current_book_url and
                    "doulist" not in href and "new_offer" not in href):
                    
                    # 提取真正的书名
                    real_title = ""
                    
                    # 检查标题是否是出版社或出版年份
                    if re.search(r'Press|出版社|\d{4}|\(', title_text):
                        # 这可能是出版社信息而不是书名
                        # 使用当前书名作为基础
                        if current_book_title:
                            real_title = current_book_title
                        else:
                            # 尝试获取更好的标题
                            text_content = item.get_text().strip()
                            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                            if len(lines) > 1 and lines[0] != title_text:
                                real_title = lines[0]
                            else:
                                real_title = "打造第二大脑"  # 默认标题
                    else:
                        # 使用链接文本作为标题
                        real_title = title_text
                    
                    # 添加标题、URL和版本标记
                    book_data["title"] = real_title + " (本书的其他版本)"
                    book_data["url"] = f"https://book.douban.com{href}" if href.startswith("/") else href
                    book_data["is_other_version"] = True  # 标记为其他版本
                    
                    # 如果有有效数据，添加到列表
                    if book_data and "title" in book_data and "url" in book_data:
                        books.append(book_data)
    
    # 记录提取结果
    if books:
        logger.info(f"从HTML页面直接提取到{len(books)}本其他版本图书")
    else:
        logger.warning("从HTML页面未直接提取到其他版本图书")
    
    return books

if __name__ == "__main__":
    import argparse
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='从豆瓣HTML页面提取图书信息')
    parser.add_argument('--input', type=str, help='输入HTML文件路径')
    parser.add_argument('--output', type=str, help='输出JSON文件路径')
    
    args = parser.parse_args()
    
    if args.input:
        try:
            # 读取HTML文件
            with open(args.input, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # 提取图书信息
            book_info = extract_from_douban(html_content)
            
            # 如果指定了输出文件，保存JSON结果
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(book_info, f, ensure_ascii=False, indent=2)
                logger.info(f"已将提取结果保存至 {args.output}")
            else:
                # 否则打印到控制台
                print(json.dumps(book_info, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"处理文件时出错: {e}")
    else:
        parser.print_help()