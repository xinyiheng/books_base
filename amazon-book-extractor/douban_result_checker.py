#!/usr/bin/env python3
import json
import sys

def check_json_format(file_path):
    """
    检查豆瓣提取结果的JSON格式是否正确
    """
    print(f"正在检查文件: {file_path}")
    
    # 读取JSON文件
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"错误: 文件'{file_path}'不存在")
        return False
    except json.JSONDecodeError as e:
        print(f"错误: JSON解析错误 - {str(e)}")
        return False

    # 检查关键字段
    required_fields = ["书名", "书本页面", "作者", "ISBN", "封面图片", "评分", "关联图书"]
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        print(f"警告: 缺少以下关键字段: {', '.join(missing_fields)}")
    
    # 检查关联图书
    related_books = data.get("关联图书", [])
    print(f"关联图书数量: {len(related_books)}")
    
    if related_books:
        book_sample = related_books[0]
        print("关联图书示例:")
        print(json.dumps(book_sample, ensure_ascii=False, indent=2))
    
    # 检查其他版本图书
    other_versions = data.get("其他版本图书", [])
    print(f"其他版本图书数量: {len(other_versions)}")
    
    if other_versions:
        version_sample = other_versions[0]
        print("其他版本图书示例:")
        print(json.dumps(version_sample, ensure_ascii=False, indent=2))
    
    # 检查评论
    comments = data.get("读者评论", [])
    print(f"读者评论数量: {len(comments)}")
    
    if comments:
        comment_sample = comments[0]
        print("评论示例:")
        print(json.dumps(comment_sample, ensure_ascii=False, indent=2))
    
    print("检查完成!")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python douban_result_checker.py <JSON文件路径>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    check_json_format(file_path) 