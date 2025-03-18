#!/usr/bin/env python3
"""
Feishu Webhook Sender
This script converts Amazon book information to Feishu format and sends it via webhook
"""

import requests
import json
import argparse
import sys

def convert_to_feishu_format(book_data):
    """
    Convert Amazon book data to Feishu format
    """
    # Extract related books titles as a string
    related_books = []
    if '关联图书' in book_data and isinstance(book_data['关联图书'], list):
        related_books = book_data['关联图书']
    elif 'related_books' in book_data and isinstance(book_data['related_books'], list):
        related_books = [book.get('title', '') for book in book_data['related_books'] if book.get('title')]
    
    # 将关联图书列表转换为字符串，每本书一行
    related_books_text = "\n".join(related_books) if related_books else ""
    
    # Extract reviews as formatted strings
    reviews = []
    if 'reviews' in book_data and isinstance(book_data['reviews'], list):
        for review in book_data['reviews']:
            reviewer = review.get('reviewer_name', '匿名')
            rating = review.get('rating', '')
            title = review.get('title', '')
            content = review.get('content', '')
            date = review.get('date', '')
            
            review_text = f"{reviewer} ({rating}): {title}\n{content}\n{date}"
            reviews.append(review_text)
    elif '读者评论' in book_data and isinstance(book_data['读者评论'], list):
        reviews = book_data['读者评论']
    
    # 将评论列表转换为字符串，每条评论之间用两个换行符分隔
    reviews_text = "\n\n".join(reviews) if reviews else ""
    
    # Create Feishu format
    feishu_data = {
        "书名": book_data.get('书名', book_data.get('title', '')),
        "书本页面": book_data.get('书本页面', book_data.get('book_url', '')),
        "作者": book_data.get('作者', book_data.get('author', '')),
        "作者页面": book_data.get('作者页面', book_data.get('author_url', '')),
        "作者简介": book_data.get('作者简介', book_data.get('author_bio', '')),
        "内容简介": book_data.get('内容简介', book_data.get('description', '')),
        "出版时间": book_data.get('出版时间', book_data.get('publication_date', '')),
        "出版社": book_data.get('出版社', book_data.get('publisher', '')),
        "ISBN": book_data.get('ISBN', book_data.get('isbn', '')),
        "封面": book_data.get('封面', book_data.get('cover_image_url', '')),
        "关联图书": related_books_text,  # 使用字符串而不是数组
        "评分": book_data.get('评分', f"Amazon: {book_data.get('amazon_rating', '')} ({book_data.get('amazon_rating_count', '')})"),
        "读者评论": reviews_text  # 使用字符串而不是数组
    }
    
    # 打印关联图书信息，便于调试
    print("\n飞书webhook中的关联图书信息:")
    print(f"类型: {type(feishu_data['关联图书'])}")
    print(feishu_data['关联图书'])
    
    return feishu_data

def send_to_feishu(data, webhook_url):
    """
    Send data to Feishu webhook
    
    Args:
        data (dict or str): Book data dictionary or path to JSON file
        webhook_url (str): Feishu webhook URL
        
    Returns:
        bool: True if sending was successful, False otherwise
    """
    try:
        # 读取JSON文件
        if isinstance(data, str):
            try:
                with open(data, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"成功从文件加载数据")
            except Exception as e:
                print(f"从文件加载数据失败: {str(e)}")
                return False
        
        # 准备飞书数据格式
        feishu_data = {
            "书名": data.get('书名', data.get('title', '')),
            "书本页面": data.get('书本页面', data.get('book_url', '')),
            "作者": data.get('作者', data.get('author', '')),
            "作者页面": data.get('作者页面', data.get('author_url', '')),
            "作者简介": data.get('作者简介', data.get('author_bio', '')),
            "内容简介": data.get('内容简介', data.get('description', '')),
            "出版时间": data.get('出版时间', data.get('publication_date', '')),
            "出版社": data.get('出版社', data.get('publisher', '')),
            "ISBN": data.get('ISBN', data.get('isbn', '')),
            "封面": data.get('封面', data.get('cover_image', data.get('imageUrl', ''))),
            "评分": data.get('评分', '')
        }
        
        # 处理关联图书，确保它是字符串
        related_books = data.get('关联图书', [])
        if isinstance(related_books, list):
            # 将列表转换为字符串
            related_books_text = []
            for book in related_books:
                if isinstance(book, dict) and 'title' in book and 'url' in book:
                    related_books_text.append(f"{book['title']} - {book['url']}")
                elif isinstance(book, str):
                    related_books_text.append(book)
            
            feishu_data['关联图书'] = "\n".join(related_books_text)
        else:
            feishu_data['关联图书'] = str(related_books)
        
        # 处理读者评论，确保它是字符串
        reviews = data.get('读者评论', [])
        if isinstance(reviews, list):
            reviews_text = []
            for review in reviews:
                if isinstance(review, dict):
                    reviewer = review.get('reviewer_name', '匿名')
                    rating = review.get('rating', '')
                    title = review.get('title', '')
                    content = review.get('content', '')
                    date = review.get('date', '')
                    
                    review_text = f"{reviewer} ({rating}星): {title}\n{content}\n{date}"
                    reviews_text.append(review_text)
                else:
                    reviews_text.append(str(review))
            
            feishu_data['读者评论'] = "\n\n".join(reviews_text)
        else:
            feishu_data['读者评论'] = str(reviews)
        
        # 发送数据到飞书webhook
        print(f"\n正在发送数据到飞书webhook: {webhook_url}")
        print(f"数据内容: {json.dumps(feishu_data, ensure_ascii=False, indent=2)}")
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(webhook_url, json=feishu_data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"成功发送数据到飞书! 响应: {response.text}")
            return True
        else:
            print(f"发送数据到飞书失败: 状态码={response.status_code}, 响应={response.text}")
            return False
    
    except Exception as e:
        print(f"发送数据到飞书时发生异常: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    parser = argparse.ArgumentParser(description='Send book information to Feishu webhook')
    parser.add_argument('--input', '-i', required=True, help='Input JSON file with book information')
    parser.add_argument('--webhook', '-w', required=True, help='Feishu webhook URL')
    args = parser.parse_args()
    
    # Load book information from JSON file
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            book_data = json.load(f)
    except Exception as e:
        print(f"Error loading book information from {args.input}: {e}", file=sys.stderr)
        return 1
    
    # Convert and send to Feishu
    success = send_to_feishu(book_data, args.webhook)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
