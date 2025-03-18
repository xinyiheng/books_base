from flask import Flask, request, jsonify, send_from_directory
import os
import json
import sys
import logging
import traceback
from pathlib import Path
from process_amazon_book import process_book

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("amazon-book-server")

app = Flask(__name__)

@app.route('/')
def home():
    return "Amazon Book Extractor Server is running!"

@app.route('/process_file', methods=['POST'])
def process_file():
    try:
        data = request.json
        
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
        
        # 记录请求数据，但不记录HTML内容（太大）
        request_data = data.copy()
        if 'html' in request_data:
            request_data['html'] = f"[HTML content ({len(data['html'])} bytes)]"
        logger.info(f"Received processing request: {json.dumps(request_data, ensure_ascii=False)}")
        
        html_content = data.get('html')
        if not html_content:
            return jsonify({"success": False, "message": "No HTML content provided"}), 400
        
        filename = data.get('filename', f"amazon_book_{str(int(time.time()))}.html")
        save_directory = data.get('saveDirectory', './output')
        feishu_webhook = data.get('feishuWebhook')
        region = data.get('region', 'us')
        url = data.get('url', '')
        
        # 确保保存目录存在
        save_directory = os.path.expanduser(save_directory)
        os.makedirs(save_directory, exist_ok=True)
        
        # 创建临时HTML文件
        html_dir = os.path.join(save_directory, "html")
        os.makedirs(html_dir, exist_ok=True)
        
        html_file_path = os.path.join(html_dir, filename)
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Saved HTML file to {html_file_path}")
        
        # 处理图书
        try:
            logger.info(f"Processing book with region: {region}, URL: {url}")
            json_file, markdown_file = process_book(
                html_file_path, 
                save_directory, 
                feishu_webhook_url=feishu_webhook,
                region=region,
                url=url
            )
            
            logger.info(f"Successfully processed book: JSON={json_file}, Markdown={markdown_file}")
            
            # 从 JSON 文件读取处理后的图书信息
            book_info = {}
            if os.path.exists(json_file):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        book_info = json.load(f)
                except Exception as e:
                    logger.error(f"Error reading JSON file: {str(e)}")
            
            return jsonify({
                "success": True,
                "message": "Book processed successfully",
                "files": {
                    "html": html_file_path,
                    "json": json_file,
                    "markdown": markdown_file
                },
                "book_info": book_info
            })
        except Exception as e:
            error_msg = str(e)
            stack_trace = traceback.format_exc()
            logger.error(f"Error processing book: {error_msg}")
            logger.error(stack_trace)
            return jsonify({
                "success": False,
                "message": f"Error processing book: {error_msg}",
                "error_details": stack_trace
            }), 500
    
    except Exception as e:
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        logger.error(f"Server error: {error_msg}")
        logger.error(stack_trace)
        return jsonify({
            "success": False,
            "message": f"Server error: {error_msg}",
            "error_details": stack_trace
        }), 500

if __name__ == "__main__":
    import time
    
    # 从配置文件加载端口设置
    port = 5001
    try:
        config_path = Path(__file__).parent.parent / "service_config.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                port = config.get('port', 5001)
                logger.info(f"Loaded port {port} from config file")
    except Exception as e:
        logger.warning(f"Failed to load config, using default port 5001: {str(e)}")
    
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True) 