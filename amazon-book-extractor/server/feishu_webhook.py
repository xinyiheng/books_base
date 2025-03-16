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

def send_to_feishu(webhook_url, book_data):
    """
    Send book data to Feishu webhook
    """
    try:
        # 读取JSON文件
        if isinstance(book_data, str):
            with open(book_data, 'r', encoding='utf-8') as f:
                book_data = json.load(f)
        
        # 转换数据格式
        feishu_data = book_data
        if not isinstance(book_data.get('关联图书', []), str):
            # 如果关联图书是列表，转换为字符串
            if isinstance(book_data.get('关联图书', []), list):
                feishu_data['关联图书'] = "\n".join(book_data['关联图书'])
        
        # 处理读者评论，确保它是字符串
        if not isinstance(book_data.get('读者评论', []), str):
            reviews = book_data.get('读者评论', [])
            if isinstance(reviews, list):
                # 如果是字典列表，提取并格式化评论内容
                formatted_reviews = []
                for review in reviews:
                    if isinstance(review, dict):
                        reviewer = review.get('reviewer_name', '匿名')
                        rating = review.get('rating', '')
                        title = review.get('title', '')
                        content = review.get('content', '')
                        date = review.get('date', '')
                        
                        review_text = f"{reviewer} ({rating}): {title}\n{content}\n{date}"
                        formatted_reviews.append(review_text)
                    else:
                        formatted_reviews.append(str(review))
                
                feishu_data['读者评论'] = "\n\n".join(formatted_reviews)
        
        # 打印关联图书信息，便于调试
        print("\n飞书webhook中的关联图书信息:")
        print(f"类型: {type(feishu_data['关联图书'])}")
        print(feishu_data['关联图书'])
        
        # 发送数据到飞书webhook
        headers = {'Content-Type': 'application/json'}
        response = requests.post(webhook_url, json=feishu_data, headers=headers)
        
        if response.status_code == 200:
            print("Successfully sent data to Feishu webhook")
        else:
            print(f"Error sending data to Feishu webhook: {response.status_code} {response.text}")
            
    except Exception as e:
        print(f"Error sending data to Feishu webhook: {str(e)}")

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
    success = send_to_feishu(args.webhook, book_data)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
