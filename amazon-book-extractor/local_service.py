#!/usr/bin/env python3
"""
Amazon Book Extractor - 本地服务
提供REST API接口，使浏览器插件能够直接与本地Python脚本通信
"""

import os
import sys

# 禁用Python字节码缓存，防止生成__pycache__目录
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import json
import logging
import tempfile
import argparse
import threading
import webbrowser
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import shutil

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("local_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LocalService")

# 导入自定义模块
try:
    from process_amazon_book import process_book
except ImportError as e:
    logger.error(f"导入模块失败: {str(e)}")
    logger.error("请确保所有必要的Python脚本都在同一目录下")
    sys.exit(1)

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 启用跨域请求支持

# 全局变量
config = {
    "save_directory": "",
    "feishu_webhook": "",
    "port": 5001,
    "auto_open_browser": True
}

@app.route('/')
def index():
    """返回服务状态页面"""
    return send_from_directory('.', 'service_status.html')

@app.route('/status', methods=['GET'])
def status():
    """返回服务状态"""
    return jsonify({
        "status": "running",
        "save_directory": config["save_directory"],
        "feishu_webhook": bool(config["feishu_webhook"]),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/config', methods=['GET', 'POST'])
def handle_config():
    """获取或更新配置"""
    global config
    
    if request.method == 'GET':
        return jsonify(config)
    
    elif request.method == 'POST':
        try:
            data = request.json
            
            if 'save_directory' in data:
                directory = data['save_directory']
                if os.path.isdir(directory):
                    config['save_directory'] = directory
                else:
                    return jsonify({"error": f"目录不存在: {directory}"}), 400
            
            if 'feishu_webhook' in data:
                config['feishu_webhook'] = data['feishu_webhook']
            
            # 保存配置到文件
            save_config()
            
            return jsonify({"message": "配置已更新", "config": config})
        
        except Exception as e:
            logger.error(f"更新配置时发生错误: {str(e)}")
            return jsonify({"error": str(e)}), 500

@app.route('/process', methods=['POST'])
def process_html():
    try:
        # 检查是否设置了保存目录
        if not config['save_directory']:
            return jsonify({"error": "未设置保存目录"}), 400
        
        # 获取请求数据
        data = request.json
        if not data or 'html' not in data or 'filename' not in data:
            return jsonify({"error": "请求数据不完整，需要提供html和filename字段"}), 400
        
        logger.info(f"收到处理HTML请求: {data.get('filename')}")
        
        html_content = data['html']
        filename = data['filename']
        save_directory = data.get('saveDirectory') or config['save_directory']
        region = data.get('region', 'us')  # 获取区域信息，默认为us
        url = data.get('url', '')  # 获取原始URL
        
        # 从URL中获取域名信息
        domain = None
        if url:
            if "amazon.co.uk" in url:
                domain = "amazon.co.uk"
            elif "amazon.co.jp" in url:
                domain = "amazon.co.jp"
            elif "amazon.com" in url:
                domain = "amazon.com"
            logger.info(f"从URL检测到域名: {domain}")
        
        # 确保文件名是安全的
        filename = os.path.basename(filename)
        if not filename.endswith('.html'):
            filename += '.html'
        
        # 确保目录结构存在
        html_dir = os.path.join(save_directory, 'html')
        if not os.path.exists(html_dir):
            os.makedirs(html_dir, exist_ok=True)
            logger.info(f"创建目录: {html_dir}")
        
        # 直接保存HTML文件到html目录
        html_file_path = os.path.join(html_dir, filename)
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"已保存HTML文件: {html_file_path}")
        
        # 处理HTML文件
        feishu_webhook = data.get('feishuWebhook') or config.get('feishu_webhook')
        logger.info(f"使用飞书Webhook: {feishu_webhook}")
        
        success = process_book(
            html_file_path, 
            save_directory, 
            feishu_webhook,
            region=region,
            url=url,
            domain=domain
        )
        
        if success:
            # 构建结果文件路径
            file_name_without_ext = os.path.splitext(filename)[0]
            
            # 提取ASIN和书名（如果存在）
            import re
            asin_match = re.search(r'amazon_book_([A-Z0-9]{10})_', file_name_without_ext)
            asin = asin_match.group(1) if asin_match else None
            
            # 尝试从文件名中提取书名
            book_title = None
            title_match = re.search(r'amazon_book_[A-Z0-9]{10}_(.+?)(?:_\d{4}-\d{2}-\d{2}T|$)', file_name_without_ext)
            if title_match:
                book_title = title_match.group(1)
            
            # 查找JSON文件路径（保持原始文件名，包含时间戳）
            json_path = os.path.join(save_directory, 'json', f"{file_name_without_ext}.json")
            
            # 查找Markdown文件路径（只包含书名）
            md_path = None
            markdown_dir = os.path.join(save_directory, 'markdown')
            
            # 尝试读取JSON文件以获取书名
            book_info = None
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        book_info = json.load(f)
                except Exception as e:
                    logger.error(f"读取JSON文件失败: {str(e)}")
            
            # 如果有JSON数据，尝试获取书名
            if book_info and 'title' in book_info and book_info['title']:
                # 清理书名，移除特殊字符
                clean_title = book_info['title'].replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
                
                # 查找匹配的Markdown文件
                if os.path.exists(markdown_dir):
                    potential_md_path = os.path.join(markdown_dir, f"{clean_title}.md")
                    if os.path.exists(potential_md_path):
                        md_path = potential_md_path
            
            # 如果没有找到匹配的Markdown文件，尝试使用从文件名中提取的书名
            if not md_path and book_title and os.path.exists(markdown_dir):
                potential_md_path = os.path.join(markdown_dir, f"{book_title}.md")
                if os.path.exists(potential_md_path):
                    md_path = potential_md_path
            
            # 如果仍然没有找到，尝试查找以ASIN开头的文件
            if not md_path and asin and os.path.exists(markdown_dir):
                for file in os.listdir(markdown_dir):
                    if file.endswith('.md'):
                        # 检查是否是以ASIN开头的文件
                        if file.startswith(f"amazon_book_{asin}"):
                            md_path = os.path.join(markdown_dir, file)
                            break
            
            # 最后的回退：使用原始文件名
            if not md_path and os.path.exists(markdown_dir):
                fallback_md_path = os.path.join(markdown_dir, f"{file_name_without_ext}.md")
                if os.path.exists(fallback_md_path):
                    md_path = fallback_md_path
            
            return jsonify({
                "success": True,
                "message": "HTML处理成功",
                "files": {
                    "html": html_file_path,
                    "json": json_path if os.path.exists(json_path) else None,
                    "markdown": md_path if md_path and os.path.exists(md_path) else None
                },
                "bookInfo": book_info
            })
        else:
            return jsonify({
                "success": False,
                "message": "处理HTML失败，请查看日志获取详细信息"
            })
    
    except Exception as e:
        logger.error(f"处理HTML时发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "message": f"处理HTML时发生错误: {str(e)}"
        }), 500

@app.route('/process_file', methods=['POST'])
def process_html_file():
    """处理指定HTML文件"""
    try:
        # 获取请求数据
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({"error": "未提供文件名"}), 400
        
        # 获取保存目录
        save_directory = config.get('save_directory')
        if not save_directory:
            return jsonify({"error": "未设置保存目录"}), 400
        
        # 构建HTML文件路径
        html_file_path = os.path.join(save_directory, 'html', filename)
        
        # 检查文件是否存在
        if not os.path.exists(html_file_path):
            return jsonify({"error": f"HTML文件不存在: {html_file_path}"}), 404
        
        logger.info(f"处理HTML文件: {html_file_path}")
        
        # 处理HTML文件
        feishu_webhook = data.get('feishuWebhook') or config.get('feishu_webhook')
        region = data.get('region', 'us')  # 获取区域信息，默认为us
        url = data.get('url', '')  # 获取原始URL
        
        # 从URL或文件名检测域名
        domain = None
        if url:
            if "amazon.co.uk" in url:
                domain = "amazon.co.uk"
            elif "amazon.co.jp" in url:
                domain = "amazon.co.jp"
            elif "amazon.com" in url:
                domain = "amazon.com"
            logger.info(f"从URL检测到域名: {domain}")
        elif "co.uk" in html_file_path:
            domain = "amazon.co.uk"
            logger.info(f"从文件名检测到域名: {domain}")
        elif "co.jp" in html_file_path:
            domain = "amazon.co.jp"
            logger.info(f"从文件名检测到域名: {domain}")
        
        success = process_book(
            html_file_path, 
            save_directory, 
            feishu_webhook,
            region=region,
            url=url,
            domain=domain
        )
        
        if success:
            # 构建结果文件路径
            file_name_without_ext = os.path.splitext(filename)[0]
            json_path = os.path.join(save_directory, 'json', f"{file_name_without_ext}.json")
            
            # 读取JSON文件以获取书籍数据
            book_info = None
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        book_info = json.load(f)
                except Exception as e:
                    logger.error(f"读取JSON文件失败: {str(e)}")
            
            # 尝试查找对应的Markdown文件（可能使用书名而不是原始文件名）
            md_path = None
            if book_info:
                title = book_info.get('标题') or book_info.get('书名') or book_info.get('title', '')
                if title:
                    # 清理标题用于文件名
                    clean_title = title.replace('/', '_').replace('\\', '_').replace(':', '_')
                    clean_title = clean_title.replace('*', '_').replace('?', '_').replace('"', '_')
                    clean_title = clean_title.replace('<', '_').replace('>', '_').replace('|', '_')
                    
                    # 限制文件名长度
                    if len(clean_title) > 100:
                        clean_title = clean_title[:100]
                    
                    possible_md_path = os.path.join(save_directory, 'markdown', f"{clean_title}.md")
                    if os.path.exists(possible_md_path):
                        md_path = possible_md_path
            
            # 如果通过标题找不到Markdown文件，则回退到使用原始文件名
            if not md_path:
                fallback_md_path = os.path.join(save_directory, 'markdown', f"{file_name_without_ext}.md")
                if os.path.exists(fallback_md_path):
                    md_path = fallback_md_path
            
            return jsonify({
                "success": True,
                "message": "处理成功",
                "files": {
                    "html": html_file_path,
                    "json": json_path,
                    "markdown": md_path
                },
                "book_info": book_info
            })
        else:
            return jsonify({
                "success": False,
                "message": "处理失败，请查看服务日志获取详细信息"
            }), 500
    
    except Exception as e:
        logger.error(f"处理HTML文件时发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/create_directories', methods=['POST'])
def create_directories():
    """创建必要的目录"""
    try:
        # 检查是否设置了保存目录
        if not config['save_directory']:
            return jsonify({"error": "未设置保存目录"}), 400
        
        # 创建目录
        html_dir = os.path.join(config['save_directory'], "html")
        json_dir = os.path.join(config['save_directory'], "json")
        markdown_dir = os.path.join(config['save_directory'], "markdown")
        
        for directory in [config['save_directory'], html_dir, json_dir, markdown_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"创建目录: {directory}")
        
        return jsonify({
            "success": True,
            "message": "目录已创建",
            "directories": {
                "root": config['save_directory'],
                "html": html_dir,
                "json": json_dir,
                "markdown": markdown_dir
            }
        })
    
    except Exception as e:
        logger.error(f"创建目录时发生错误: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/sync-data', methods=['POST'])
def sync_data():
    """同步数据到本地或从本地同步到云端"""
    try:
        data = request.json
        sync_type = data.get('sync_type', 'cloud_to_local')  # 默认从云端同步到本地
        local_directory = data.get('local_directory')
        
        if not local_directory:
            return jsonify({'success': False, 'message': '未提供本地目录'})
        
        # 确保目录存在
        for subdir in ['html', 'json', 'markdown']:
            os.makedirs(os.path.join(local_directory, subdir), exist_ok=True)
        
        if sync_type == 'local_to_cloud':
            # 从本地同步到云端
            files_synced = sync_local_to_cloud(local_directory, config['save_directory'])
            return jsonify({'success': True, 'message': f'已从本地同步{files_synced}个文件到云端'})
        else:
            # 从云端同步到本地
            files_synced = sync_cloud_to_local(config['save_directory'], local_directory)
            return jsonify({'success': True, 'message': f'已从云端同步{files_synced}个文件到本地'})
    except Exception as e:
        logger.error(f"同步数据时出错: {str(e)}")
        return jsonify({'success': False, 'message': f'同步数据时出错: {str(e)}'})

def sync_local_to_cloud(local_dir, cloud_dir):
    """将本地文件同步到云端"""
    files_synced = 0
    
    for subdir in ['html', 'json', 'markdown']:
        local_subdir = os.path.join(local_dir, subdir)
        cloud_subdir = os.path.join(cloud_dir, subdir)
        
        if not os.path.exists(local_subdir):
            continue
            
        os.makedirs(cloud_subdir, exist_ok=True)
        
        for filename in os.listdir(local_subdir):
            local_file = os.path.join(local_subdir, filename)
            cloud_file = os.path.join(cloud_subdir, filename)
            
            # 只同步本地较新的文件
            if not os.path.exists(cloud_file) or os.path.getmtime(local_file) > os.path.getmtime(cloud_file):
                shutil.copy2(local_file, cloud_file)
                files_synced += 1
    
    return files_synced

def sync_cloud_to_local(cloud_dir, local_dir):
    """将云端文件同步到本地"""
    files_synced = 0
    
    for subdir in ['html', 'json', 'markdown']:
        cloud_subdir = os.path.join(cloud_dir, subdir)
        local_subdir = os.path.join(local_dir, subdir)
        
        if not os.path.exists(cloud_subdir):
            continue
            
        os.makedirs(local_subdir, exist_ok=True)
        
        for filename in os.listdir(cloud_subdir):
            cloud_file = os.path.join(cloud_subdir, filename)
            local_file = os.path.join(local_subdir, filename)
            
            # 只同步云端较新的文件
            if not os.path.exists(local_file) or os.path.getmtime(cloud_file) > os.path.getmtime(local_file):
                shutil.copy2(cloud_file, local_file)
                files_synced += 1
    
    return files_synced

def load_config():
    """从文件加载配置"""
    global config
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'service_config.json')
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # 更新配置，但保留默认值
                for key in loaded_config:
                    if key in config:
                        config[key] = loaded_config[key]
            logger.info("已加载配置")
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")

def save_config():
    """保存配置到文件"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'service_config.json')
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info("已保存配置")
    except Exception as e:
        logger.error(f"保存配置失败: {str(e)}")

def create_status_page():
    """创建服务状态页面"""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Amazon Book Extractor - 本地服务状态</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }
        h1 {
            color: #232f3e;
            border-bottom: 2px solid #ff9900;
            padding-bottom: 10px;
        }
        .status-card {
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .status-item {
            margin-bottom: 10px;
        }
        .label {
            font-weight: bold;
            display: inline-block;
            width: 150px;
        }
        .value {
            display: inline-block;
        }
        .success {
            color: #28a745;
        }
        .error {
            color: #dc3545;
        }
        .warning {
            color: #ffc107;
        }
        .refresh-btn {
            background-color: #232f3e;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .refresh-btn:hover {
            background-color: #1a2530;
        }
    </style>
</head>
<body>
    <h1>Amazon Book Extractor - 本地服务状态</h1>
    
    <div class="status-card">
        <h2>服务信息</h2>
        <div class="status-item">
            <span class="label">状态:</span>
            <span class="value success" id="service-status">运行中</span>
        </div>
        <div class="status-item">
            <span class="label">启动时间:</span>
            <span class="value" id="start-time">-</span>
        </div>
        <div class="status-item">
            <span class="label">运行时间:</span>
            <span class="value" id="uptime">-</span>
        </div>
    </div>
    
    <div class="status-card">
        <h2>配置信息</h2>
        <div class="status-item">
            <span class="label">保存目录:</span>
            <span class="value" id="save-directory">-</span>
        </div>
        <div class="status-item">
            <span class="label">飞书Webhook:</span>
            <span class="value" id="feishu-webhook">-</span>
        </div>
        <div class="status-item">
            <span class="label">服务端口:</span>
            <span class="value" id="service-port">-</span>
        </div>
    </div>
    
    <div class="status-card">
        <h2>使用说明</h2>
        <p>本服务为Amazon Book Extractor浏览器插件提供后端支持，实现自动化处理亚马逊图书信息。</p>
        <p>请确保浏览器插件已正确配置本地服务地址。</p>
        <p>如需更改配置，请使用浏览器插件的设置页面。</p>
    </div>
    
    <button class="refresh-btn" onclick="refreshStatus()">刷新状态</button>
    
    <script>
        // 服务启动时间
        let startTime = new Date();
        
        // 页面加载时获取状态
        window.onload = function() {
            refreshStatus();
            // 每30秒自动刷新一次
            setInterval(refreshStatus, 30000);
        };
        
        // 刷新状态
        function refreshStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('service-status').textContent = data.status;
                    document.getElementById('save-directory').textContent = data.save_directory || '未设置';
                    document.getElementById('feishu-webhook').textContent = data.feishu_webhook ? '已配置' : '未配置';
                    document.getElementById('service-port').textContent = window.location.port;
                    
                    // 更新时间信息
                    document.getElementById('start-time').textContent = startTime.toLocaleString();
                    const now = new Date();
                    const diff = Math.floor((now - startTime) / 1000);
                    document.getElementById('uptime').textContent = formatUptime(diff);
                })
                .catch(error => {
                    console.error('获取状态失败:', error);
                    document.getElementById('service-status').textContent = '错误';
                    document.getElementById('service-status').className = 'value error';
                });
        }
        
        // 格式化运行时间
        function formatUptime(seconds) {
            const days = Math.floor(seconds / 86400);
            seconds %= 86400;
            const hours = Math.floor(seconds / 3600);
            seconds %= 3600;
            const minutes = Math.floor(seconds / 60);
            seconds %= 60;
            
            let result = '';
            if (days > 0) result += days + '天 ';
            if (hours > 0 || days > 0) result += hours + '小时 ';
            if (minutes > 0 || hours > 0 || days > 0) result += minutes + '分钟 ';
            result += seconds + '秒';
            
            return result;
        }
    </script>
</body>
</html>
"""
    
    status_page_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'service_status.html')
    
    try:
        with open(status_page_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"已创建服务状态页面: {status_page_path}")
    except Exception as e:
        logger.error(f"创建服务状态页面失败: {str(e)}")

def open_browser():
    """在浏览器中打开服务状态页面"""
    url = f"http://localhost:{config['port']}/"
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    logger.info(f"正在浏览器中打开服务状态页面: {url}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Amazon Book Extractor - 本地服务")
    parser.add_argument("--port", type=int, default=5001, help="服务端口号")
    parser.add_argument("--directory", help="保存目录")
    parser.add_argument("--webhook", help="飞书Webhook URL")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    
    args = parser.parse_args()
    
    # 加载配置
    load_config()
    
    # 从环境变量读取配置（用于云部署）
    import os
    env_port = os.environ.get('PORT')
    env_directory = os.environ.get('SAVE_DIRECTORY')
    env_webhook = os.environ.get('FEISHU_WEBHOOK')
    
    # 更新配置，优先级：命令行参数 > 环境变量 > 配置文件
    if args.port:
        config["port"] = args.port
    elif env_port:
        config["port"] = int(env_port)
        
    if args.directory:
        config["save_directory"] = args.directory
    elif env_directory:
        config["save_directory"] = env_directory
        
    if args.webhook:
        config["feishu_webhook"] = args.webhook
    elif env_webhook:
        config["feishu_webhook"] = env_webhook
        
    if args.no_browser:
        config["auto_open_browser"] = False
    
    # 保存配置
    save_config()
    
    # 创建服务状态页面
    create_status_page()
    
    # 启动服务
    logger.info(f"正在启动本地服务，端口: {config['port']}")
    
    if config["auto_open_browser"] and not os.environ.get('CLOUD_DEPLOYMENT'):
        open_browser()
    
    app.run(host='0.0.0.0', port=config['port'])

if __name__ == "__main__":
    main()
