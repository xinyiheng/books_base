#!/usr/bin/env python3
"""
自动导入模块 - 用于在生成JSON数据后直接导入到TheBrain
可以被local_service直接调用，无需启动单独的webhook服务
"""

import os
import json
import logging
from brain_importer import BrainImporter, process_markdown_content, convert_to_markdown

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_importer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AutoImporter")

# 固定配置信息
BRAIN_ID = "53d07455-e094-44a5-a29b-82e0314abed1"
API_KEY = "720f806f2855fd97727b2677e2b0b33935895ed1645260a9f58576644e2bc804"
SOURCE_THOUGHT_ID = "d9bb8a54-cfec-4ed4-986a-ae1c53471207"

def save_to_json_file(book_data, base_dir=None):
    """将图书数据保存到JSON文件（用于备份）"""
    try:
        # 创建保存目录
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        save_dir = os.path.join(base_dir, "json_backup")
        os.makedirs(save_dir, exist_ok=True)
        
        # 生成文件名
        book_title = book_data.get('标题') or book_data.get('书名') or book_data.get('title', 'unknown')
        # 清理文件名
        book_title = "".join(c for c in book_title if c.isalnum() or c in [' ', '-', '_'])
        book_title = book_title.strip()
        if not book_title:
            book_title = "unknown"
        
        # 保存JSON文件
        import time
        timestamp = time.strftime("%Y%m%d%H%M%S")
        filepath = os.path.join(save_dir, f"{book_title}_{timestamp}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(book_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存图书数据到文件: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"保存图书数据到JSON文件时出错: {str(e)}")
        return None

def auto_import_book(book_data):
    """
    自动将书籍JSON数据导入到TheBrain
    
    Args:
        book_data: 字典格式的书籍数据
        
    Returns:
        dict: 包含导入结果的字典
        {
            "success": True/False,
            "message": "成功/错误信息",
            "thought_id": "创建的思想ID（如果成功）"
        }
    """
    try:
        # 提取书名
        book_title = book_data.get('标题') or book_data.get('书名') or book_data.get('title', '')
        if not book_title:
            logger.error("无法从JSON中提取书名")
            return {"success": False, "message": "无法从数据中提取书名"}
        
        logger.info(f"开始处理书籍数据: {book_title}")
        
        # 保存原始数据到文件(备份)
        backup_file = save_to_json_file(book_data)
        if backup_file:
            logger.info(f"已备份原始数据到: {backup_file}")
        
        # 生成Markdown内容
        logger.info("生成Markdown内容...")
        md_content = convert_to_markdown(book_data)
        
        # 处理Markdown内容，移除开头的属性信息
        logger.info("处理Markdown内容，移除YAML frontmatter...")
        md_content = process_markdown_content(md_content)
        
        # 打印API信息，便于调试
        logger.info(f"使用的API信息 - Brain ID: {BRAIN_ID}")
        logger.info(f"API Key前8位: {API_KEY[:8]}...")
        if SOURCE_THOUGHT_ID:
            logger.info(f"源Thought ID: {SOURCE_THOUGHT_ID}")
        
        # 初始化Brain导入器
        brain_importer = BrainImporter(BRAIN_ID, API_KEY)
        
        # 创建Thought
        logger.info(f"尝试创建Thought: {book_title}")
        thought_data = brain_importer.create_thought(book_title, source_thought_id=SOURCE_THOUGHT_ID)
        if not thought_data:
            logger.error(f"创建Thought失败")
            return {"success": False, "message": "创建Thought失败，请检查API地址和认证信息"}
        
        # 提取Thought ID
        thought_id = thought_data.get('id')
        if not thought_id:
            logger.error(f"无法获取Thought ID")
            return {"success": False, "message": "无法获取Thought ID"}
        
        logger.info(f"成功创建Thought，ID: {thought_id}")
        
        # 更新Note内容
        logger.info(f"尝试更新Note内容...")
        success = brain_importer.update_note(thought_id, md_content)
        
        if success:
            logger.info(f"成功将书籍 '{book_title}' 导入到The Brain")
            return {
                "success": True, 
                "message": f"成功导入书籍 '{book_title}'",
                "thought_id": thought_id
            }
        else:
            logger.error(f"将书籍导入到The Brain失败")
            return {"success": False, "message": "更新Note失败，请检查API访问"}
            
    except Exception as e:
        logger.exception(f"导入书籍时出错: {str(e)}")
        return {"success": False, "message": f"处理导入时出错: {str(e)}"}

def auto_import_from_file(json_file_path):
    """
    从JSON文件自动导入书籍数据到TheBrain
    
    Args:
        json_file_path: JSON文件路径
        
    Returns:
        dict: 包含导入结果的字典
    """
    try:
        # 读取JSON文件
        with open(json_file_path, 'r', encoding='utf-8') as f:
            book_data = json.load(f)
        
        # 调用自动导入函数
        return auto_import_book(book_data)
    
    except Exception as e:
        logger.exception(f"从文件导入时出错: {str(e)}")
        return {"success": False, "message": f"从文件导入时出错: {str(e)}"}

# 在文件最后添加测试函数
def test_api_connection():
    """测试API连接是否正常"""
    import requests
    
    logger.info(f"测试API连接 - Brain ID: {BRAIN_ID}")
    logger.info(f"API Key前8位: {API_KEY[:8]}...")
    
    # 使用正确的headers
    headers = {
        "Accept": "*/*",
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json-patch+json"
    }
    
    # 测试Brain接口
    print("\n=== API连接测试 ===")
    
    # 测试获取Brain信息
    brain_url = f"https://api.bra.in/brains/{BRAIN_ID}"
    try:
        print(f"测试获取Brain信息: {brain_url}")
        brain_response = requests.get(brain_url, headers=headers, timeout=10)
        
        if brain_response.status_code == 200:
            print(f"✅ 成功获取Brain信息! 状态码: {brain_response.status_code}")
            try:
                data = brain_response.json()
                brain_name = data.get('name', '')
                print(f"Brain名称: {brain_name}")
            except:
                pass
        else:
            print(f"❌ 获取Brain信息失败! 状态码: {brain_response.status_code}")
    except Exception as e:
        print(f"❌ 获取Brain信息时出错: {str(e)}")
    
    # 测试创建Thought
    print("\n=== 测试创建Thought ===")
    from datetime import datetime
    test_thought_name = f"测试Thought {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # 正确的创建thought API路径
    thoughts_url = f"https://api.bra.in/thoughts/{BRAIN_ID}"
    payload = {
        "name": test_thought_name,
        "kind": 1,
        "acType": 0
    }
    
    if SOURCE_THOUGHT_ID:
        payload["sourceThoughtId"] = SOURCE_THOUGHT_ID
        payload["relation"] = 1
        
    try:
        print(f"尝试创建Thought: {test_thought_name}")
        print(f"请求URL: {thoughts_url}")
        print(f"请求头: Accept={headers['Accept']}, Content-Type={headers['Content-Type']}")
        print(f"请求体: {json.dumps(payload, ensure_ascii=False)}")
        
        response = requests.post(thoughts_url, headers=headers, json=payload, timeout=15)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text[:200]}")
        
        if response.status_code in [200, 201]:
            thought_data = response.json()
            thought_id = thought_data.get('id')
            if thought_id:
                print(f"✅ 成功创建Thought! ID: {thought_id}")
                
                # 测试更新note
                print("\n=== 测试更新Note ===")
                notes_url = f"https://api.bra.in/notes/{BRAIN_ID}/{thought_id}/append"
                note_payload = {
                    "markdown": f"这是一个测试Note，创建于 {datetime.now()}"
                }
                
                try:
                    print(f"尝试更新Note，请求URL: {notes_url}")
                    note_response = requests.post(notes_url, headers=headers, json=note_payload, timeout=15)
                    
                    if note_response.status_code in [200, 201, 204]:
                        print(f"✅ 成功更新Note!")
                        return True
                    else:
                        print(f"❌ 更新Note失败! 状态码: {note_response.status_code}")
                        print(f"响应内容: {note_response.text[:200]}")
                except Exception as e:
                    print(f"❌ 更新Note时出错: {str(e)}")
            else:
                print(f"❓ 创建成功但没有返回ID")
        else:
            print(f"❌ 创建Thought失败! 状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ 创建Thought时出错: {str(e)}")
    
    # 测试结果总结
    print("\n❌ API测试未能完全成功")
    return False

# 修改主函数，支持测试API连接
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test-api":
            test_api_connection()
        else:
            json_file = sys.argv[1]
            result = auto_import_from_file(json_file)
            print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("用法: python auto_brain_importer.py <json文件路径|--test-api>")
        print("       --test-api    测试API连接") 