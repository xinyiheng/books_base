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
    # 确保能够导入父目录中的模块
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
        
    # 尝试导入auto_brain_importer模块，用于自动导入到TheBrain
    try:
        from auto_brain_importer import auto_import_book
        logger.info("成功导入auto_brain_importer模块")
    except ImportError as e:
        logger.warning(f"导入auto_brain_importer模块失败: {str(e)}")
        logger.warning("将无法自动导入数据到TheBrain")
    
    # 导入其他模块
    from json_to_markdown import convert_to_markdown
    from feishu_webhook import send_to_feishu
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
    """首页 - 显示服务状态页面"""
    return send_from_directory('.', 'status.html')

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
        
        # 获取飞书webhook
        feishu_webhook = data.get('feishuWebhook') or config.get('feishu_webhook')
        logger.info(f"使用飞书Webhook: {feishu_webhook}")
        
        # 将处理任务放入后台线程执行，不阻塞主线程
        def process_in_background():
            try:
                process_book(
                    html_file_path, 
                    save_directory, 
                    feishu_webhook,
                    region=region,
                    url=url,
                    domain=domain
                )
                logger.info(f"后台处理完成: {filename}")
            except Exception as e:
                logger.error(f"后台处理出错: {str(e)}")
        
        # 启动后台线程
        threading.Thread(target=process_in_background).start()
        logger.info(f"已启动后台处理线程: {filename}")
        
        # 构建结果文件路径 - 只返回HTML路径，因为其他文件还在处理中
        file_name_without_ext = os.path.splitext(filename)[0]
        json_path = os.path.join(save_directory, 'json', f"{file_name_without_ext}.json")
        
        # 立即返回成功响应
        return jsonify({
            "success": True,
            "message": "已启动处理，将在后台继续执行",
            "files": {
                "html": html_file_path,
            },
            "in_progress": True
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
        
        # 获取参数
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
        
        # 将处理任务放入后台线程执行
        def process_in_background():
            try:
                process_book(
                    html_file_path, 
                    save_directory, 
                    feishu_webhook,
                    region=region,
                    url=url,
                    domain=domain
                )
                logger.info(f"后台处理完成: {filename}")
            except Exception as e:
                logger.error(f"后台处理出错: {str(e)}")
        
        # 启动后台线程
        threading.Thread(target=process_in_background).start()
        logger.info(f"已启动后台处理线程: {filename}")
        
        # 构建预期的结果文件路径
        file_name_without_ext = os.path.splitext(filename)[0]
        json_path = os.path.join(save_directory, 'json', f"{file_name_without_ext}.json")
        
        # 立即返回成功响应
        return jsonify({
            "success": True,
            "message": "已启动处理，将在后台继续执行",
            "files": {
                "html": html_file_path
            },
            "in_progress": True
        })
    
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
        
        # 是否为iCloud路径
        is_icloud = "Mobile Documents" in config['save_directory'] or "com~apple~CloudDocs" in config['save_directory']
        if is_icloud:
            logger.info(f"创建目录时检测到iCloud路径: {config['save_directory']}")
        
        # 创建目录
        html_dir = os.path.join(config['save_directory'], "html")
        json_dir = os.path.join(config['save_directory'], "json")
        markdown_dir = os.path.join(config['save_directory'], "markdown")
        
        created_dirs = []
        failed_dirs = []
        
        for directory in [config['save_directory'], html_dir, json_dir, markdown_dir]:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                    logger.info(f"创建目录: {directory}")
                    created_dirs.append(directory)
                    
                    # 为iCloud路径验证写入权限
                    if is_icloud:
                        try:
                            test_file = os.path.join(directory, ".test_write_permission")
                            with open(test_file, 'w') as f:
                                f.write("test")
                            os.remove(test_file)
                            logger.info(f"已验证目录权限: {directory}")
                        except Exception as e:
                            logger.error(f"目录权限验证失败: {directory}: {str(e)}")
                            failed_dirs.append(f"{directory} (权限错误: {str(e)})")
                except Exception as e:
                    logger.error(f"创建目录失败: {directory}: {str(e)}")
                    failed_dirs.append(f"{directory} (创建失败: {str(e)})")
        
        response = {
            "success": len(failed_dirs) == 0,
            "message": "目录已创建" if len(failed_dirs) == 0 else f"部分目录创建失败: {', '.join(failed_dirs)}",
            "directories": {
                "root": config['save_directory'],
                "html": html_dir,
                "json": json_dir,
                "markdown": markdown_dir
            },
            "created": created_dirs
        }
        
        if len(failed_dirs) > 0:
            response["failed"] = failed_dirs
            
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"创建目录时发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
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

@app.route('/save-jd-data', methods=['POST'])
def save_jd_data():
    """处理并保存从JD提取的图书数据"""
    try:
        # 检查是否设置了保存目录
        if not config['save_directory']:
            return jsonify({"error": "未设置保存目录"}), 400
        
        # 获取请求数据
        data = request.json
        if not data or 'filename' not in data or 'data' not in data:
            return jsonify({"error": "请求数据不完整，需要提供filename和data字段"}), 400
        
        logger.info(f"收到JD图书数据: {data.get('filename')}")
        
        # 提取数据
        filename = data['filename']
        json_data = data['data']
        url = data.get('url', '')
        timestamp = data.get('timestamp', datetime.now().isoformat())
        
        # 解析JSON数据，获取书名和ISBN
        book_title = filename
        book_data = None
        try:
            book_data = json.loads(json_data)
            book_title = book_data.get('书名', '')
            book_isbn = book_data.get('ISBN', '')
            
            if book_title:
                # 以书名命名文件，添加时间戳
                safe_title = ''.join(c for c in book_title if c.isalnum() or c in ' -_.')[:100]  # 限制长度并保证安全
                timestamp_str = datetime.now().strftime('%Y-%m-%dT%H-%M-%S-%f')[:-3] + 'Z'
                filename = f"{safe_title}_{timestamp_str}.json"
                logger.info(f"使用书名作为文件名: {filename}")
            elif book_isbn:
                # 如果没有书名但有ISBN，使用ISBN作为文件名
                timestamp_str = datetime.now().strftime('%Y-%m-%dT%H-%M-%S-%f')[:-3] + 'Z'
                filename = f"jd_book_{book_isbn}_{timestamp_str}.json"
        except Exception as e:
            logger.warning(f"无法解析JSON数据获取书名或ISBN: {str(e)}")
        
        # 确保文件名是安全的
        filename = os.path.basename(filename)
        if not filename.endswith('.json'):
            filename += '.json'
        
        # 确保json目录存在
        json_dir = os.path.join(config['save_directory'], 'json')
        if not os.path.exists(json_dir):
            os.makedirs(json_dir, exist_ok=True)
            logger.info(f"创建目录: {json_dir}")
        
        # 保存JSON文件
        json_file_path = os.path.join(json_dir, filename)
        with open(json_file_path, 'w', encoding='utf-8') as f:
            f.write(json_data)
        
        logger.info(f"已保存JD图书数据: {json_file_path}")
        
        # 添加: 自动导入到TheBrain
        thought_id = None
        if book_data:
            try:
                # 检查是否可以导入auto_brain_importer模块
                parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                auto_importer_path = os.path.join(parent_dir, "auto_brain_importer.py")
                
                if os.path.exists(auto_importer_path):
                    # 导入auto_brain_importer模块
                    sys.path.insert(0, parent_dir)
                    from auto_brain_importer import auto_import_book
                    
                    logger.info(f"开始自动导入JD图书到TheBrain: {book_title}")
                    
                    # 调用导入函数
                    import_result = auto_import_book(book_data)
                    
                    if import_result.get("success"):
                        logger.info(f"成功将JD图书 '{book_title}' 导入到TheBrain")
                        thought_id = import_result.get('thought_id')
                        logger.info(f"Thought ID: {thought_id}")
                    else:
                        logger.error(f"导入JD图书到TheBrain失败: {import_result.get('message')}")
                else:
                    logger.warning(f"未找到auto_brain_importer.py，跳过导入到TheBrain。路径: {auto_importer_path}")
            except Exception as e:
                logger.error(f"导入JD图书到TheBrain时出错: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                # 继续处理，不让导入错误影响正常流程
        
        # 返回成功响应
        response = {
            "success": True,
            "message": f"数据已保存: {filename}",
            "file_path": json_file_path
        }
        
        # 如果导入到TheBrain成功，添加thought_id到响应中
        if thought_id:
            response["thought_id"] = thought_id
            response["message"] += f" 并已导入到TheBrain"
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"保存JD图书数据时发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "message": f"保存数据时发生错误: {str(e)}"
        }), 500

# 添加处理中文网站数据的API端点
@app.route('/process_chinese_site', methods=['POST'])
def process_chinese_site():
    """处理从中文网站(京东、当当、豆瓣)提取的图书数据"""
    try:
        data = request.json
        json_data = data.get('json_data')
        filename = data.get('filename')
        save_directory = data.get('saveDirectory')
        site_type = data.get('site_type')
        feishu_webhook = data.get('feishuWebhook')
        
        if not save_directory:
            save_directory = config["save_directory"]
        
        if not save_directory:
            return jsonify({
                'success': False,
                'message': '未设置保存目录'
            })
        
        try:
            # 确保json和markdown目录存在
            json_dir = os.path.join(save_directory, 'json')
            markdown_dir = os.path.join(save_directory, 'markdown')
            os.makedirs(json_dir, exist_ok=True)
            os.makedirs(markdown_dir, exist_ok=True)
            
            # 保存JSON文件
            json_path = os.path.join(json_dir, f"{filename}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            # 生成Markdown文件
            md_content = convert_to_markdown(json_data)
            md_path = os.path.join(markdown_dir, f"{filename}.md")
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            # 发送webhook请求(如果有)
            if feishu_webhook or config.get('feishu_webhook'):
                webhook_url = feishu_webhook or config.get('feishu_webhook')
                try:
                    send_to_feishu(json_data, webhook_url)
                    logger.info(f"已将数据发送到飞书webhook")
                except Exception as e:
                    logger.error(f"发送数据到飞书失败: {str(e)}")
            
            # 添加: 自动导入到TheBrain
            try:
                # 检查是否可以导入auto_brain_importer模块
                parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                auto_importer_path = os.path.join(parent_dir, "auto_brain_importer.py")
                
                if os.path.exists(auto_importer_path):
                    # 导入auto_brain_importer模块
                    sys.path.insert(0, parent_dir)
                    from auto_brain_importer import auto_import_book
                    
                    book_title = json_data.get('标题') or json_data.get('书名') or json_data.get('title', filename)
                    logger.info(f"开始自动导入中文网站图书到TheBrain: {book_title}")
                    
                    # 调用导入函数
                    import_result = auto_import_book(json_data)
                    
                    if import_result.get("success"):
                        logger.info(f"成功将中文网站图书 '{book_title}' 导入到TheBrain")
                        logger.info(f"Thought ID: {import_result.get('thought_id')}")
                    else:
                        logger.error(f"导入中文网站图书到TheBrain失败: {import_result.get('message')}")
                else:
                    logger.warning(f"未找到auto_brain_importer.py，跳过导入到TheBrain。路径: {auto_importer_path}")
            except Exception as e:
                logger.error(f"导入中文网站图书到TheBrain时出错: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                # 继续处理，不让导入错误影响正常流程
            
            return jsonify({
                'success': True,
                'files': {
                    'json': json_path,
                    'markdown': md_path
                },
                'message': f'成功处理{site_type}图书数据'
            })
            
        except Exception as e:
            logger.error(f"处理中文网站数据时发生错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'处理数据失败: {str(e)}'
            })
    
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'处理请求失败: {str(e)}'
        })

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
    
    # 特殊处理iCloud路径
    if config["save_directory"]:
        # 对于包含空格和特殊字符的路径，特别是iCloud路径
        if "Mobile Documents" in config["save_directory"] or "com~apple~CloudDocs" in config["save_directory"]:
            logger.info(f"检测到iCloud路径: {config['save_directory']}")
            # 1. 确保路径格式正确
            config["save_directory"] = config["save_directory"].replace("\\", "/")
            
            # 2. 验证路径是否存在，如果不存在则尝试创建
            if not os.path.exists(config["save_directory"]):
                try:
                    os.makedirs(config["save_directory"], exist_ok=True)
                    logger.info(f"已创建iCloud目录: {config['save_directory']}")
                except Exception as e:
                    logger.error(f"创建iCloud目录失败: {str(e)}")
                    print(f"错误: 无法创建iCloud目录 {config['save_directory']}: {str(e)}")
                    # 不立即退出，继续尝试
            
            # 3. 验证目录权限
            try:
                test_file = os.path.join(config["save_directory"], ".test_write_permission")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                logger.info(f"已验证iCloud目录权限: {config['save_directory']}")
            except Exception as e:
                logger.error(f"iCloud目录权限验证失败: {str(e)}")
                print(f"警告: iCloud目录可能没有足够权限: {str(e)}")
                # 不立即退出，继续尝试
    
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
