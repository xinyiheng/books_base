#!/usr/bin/env python3
"""
CSS选择器测试工具
用于快速测试CSS选择器在不同网站上的提取效果
支持对提取的内容进行可视化展示，帮助优化选择器
"""

import os
import sys
import json
import argparse
import webbrowser
import traceback
from bs4 import BeautifulSoup
from pathlib import Path
import tempfile
import logging

# 引入多源提取器
from multi_source_extractor import test_selector, registry

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SelectorTester")

def generate_html_report(selector_result, html_content, output_file=None):
    """生成HTML报告展示选择器测试结果"""
    # 创建临时文件（如果未指定输出文件）
    if not output_file:
        temp_dir = tempfile.gettempdir()
        output_file = os.path.join(temp_dir, "selector_test_result.html")
    
    # 生成HTML内容
    html_output = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>选择器测试结果 - {selector_result.get('selector', '')}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                max-width: 1200px;
                margin: 0 auto;
                background-color: #f7f9fc;
            }}
            .header {{
                background-color: #4CAF50;
                color: white;
                padding: 10px 15px;
                border-radius: 5px 5px 0 0;
            }}
            .container {{
                background-color: white;
                border-radius: 5px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            .content {{
                padding: 15px;
            }}
            .selector-info {{
                background-color: #e8f5e9;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .result-item {{
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 10px;
                border-left: 4px solid #4CAF50;
            }}
            pre {{
                background-color: #f1f1f1;
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
            }}
            .error {{
                color: #d32f2f;
                background-color: #ffebee;
                padding: 10px;
                border-radius: 5px;
                border-left: 4px solid #d32f2f;
            }}
            .highlight {{
                background-color: yellow;
            }}
            .tabs {{
                display: flex;
                border-bottom: 1px solid #ddd;
            }}
            .tab {{
                padding: 10px 15px;
                cursor: pointer;
                background-color: #f1f1f1;
                border: 1px solid #ddd;
                border-bottom: none;
                margin-right: 5px;
                border-radius: 5px 5px 0 0;
            }}
            .tab.active {{
                background-color: white;
                border-bottom: 1px solid white;
            }}
            .tab-content {{
                display: none;
                padding: 15px;
                border: 1px solid #ddd;
                border-top: none;
            }}
            .tab-content.active {{
                display: block;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>CSS选择器测试结果</h1>
            </div>
            <div class="content">
                <div class="selector-info">
                    <h2>测试详情</h2>
                    <p><strong>选择器:</strong> {selector_result.get('selector', '')}</p>
                    <p><strong>属性:</strong> {selector_result.get('attribute', '文本内容')}</p>
                    <p><strong>匹配元素数:</strong> {selector_result.get('count', 0)}</p>
                </div>
                
                <div class="tabs">
                    <div class="tab active" onclick="openTab(event, 'results')">匹配结果</div>
                    <div class="tab" onclick="openTab(event, 'html-view')">HTML预览</div>
                </div>
                
                <div id="results" class="tab-content active">
                    <h3>匹配结果</h3>
    """
    
    # 添加结果项或错误信息
    if 'error' in selector_result:
        html_output += f"""
                    <div class="error">
                        <h3>错误</h3>
                        <p>{selector_result['error']}</p>
                    </div>
        """
    else:
        for item in selector_result.get('results', []):
            html_output += f"""
                    <div class="result-item">
                        <h4>结果 #{item['index'] + 1}</h4>
                        <pre>{item['content']}</pre>
                    </div>
            """
    
    # 添加HTML预览
    html_output += f"""
                </div>
                
                <div id="html-view" class="tab-content">
                    <h3>HTML预览 (带有匹配元素的高亮显示)</h3>
                    <div>
                        <pre id="html-preview">{html_content}</pre>
                    </div>
                    <script>
                        // 简单的HTML高亮函数，实际情况下可能需要更复杂的实现
                        function highlightHtml() {{
                            const selector = "{selector_result.get('selector', '')}";
                            try {{
                                // 这只是一个简化的实现，实际情况下可能需要更精确的处理
                                const htmlPreview = document.getElementById('html-preview');
                                const content = htmlPreview.textContent;
                                
                                // 将选择器转换为正则表达式模式 (这是一个简化版本)
                                let pattern = selector.replace(/\./g, '\\\\.');
                                pattern = pattern.replace(/\#/g, '\\\\#');
                                pattern = pattern.replace(/\[/g, '\\\\[');
                                pattern = pattern.replace(/\]/g, '\\\\]');
                                
                                // 尝试找到选择器对应的HTML元素
                                // 这是一个非常简化的实现，可能无法准确匹配所有情况
                                const regex = new RegExp('(<[^>]*' + pattern + '[^>]*>.*?</.*?>)', 'gs');
                                const highlightedContent = content.replace(regex, '<span class="highlight">$1</span>');
                                
                                htmlPreview.innerHTML = highlightedContent;
                            }} catch(e) {{
                                console.error("高亮处理失败:", e);
                            }}
                        }}
                        
                        // 页面加载后执行高亮
                        window.onload = highlightHtml;
                    </script>
                </div>
                
                <script>
                    function openTab(evt, tabName) {{
                        var i, tabcontent, tablinks;
                        
                        // 隐藏所有标签内容
                        tabcontent = document.getElementsByClassName("tab-content");
                        for (i = 0; i < tabcontent.length; i++) {{
                            tabcontent[i].className = tabcontent[i].className.replace(" active", "");
                        }}
                        
                        // 移除所有标签按钮的高亮
                        tablinks = document.getElementsByClassName("tab");
                        for (i = 0; i < tablinks.length; i++) {{
                            tablinks[i].className = tablinks[i].className.replace(" active", "");
                        }}
                        
                        // 显示当前标签内容并高亮按钮
                        document.getElementById(tabName).className += " active";
                        evt.currentTarget.className += " active";
                    }}
                </script>
            </div>
        </div>
    </body>
    </html>
    """
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_output)
    
    logger.info(f"HTML报告已生成: {output_file}")
    return output_file

def read_html_file(file_path):
    """读取HTML文件内容"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1']
    html_content = None
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                html_content = f.read()
            logger.info(f"成功使用 {encoding} 编码读取文件")
            return html_content
        except UnicodeDecodeError:
            continue
    
    if html_content is None:
        logger.error("无法使用任何编码读取文件")
        return None
    
    return html_content

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="CSS选择器测试工具")
    parser.add_argument("file", help="要处理的HTML文件路径")
    parser.add_argument("selector", help="要测试的CSS选择器")
    parser.add_argument("--attr", "-a", help="要提取的属性（默认为文本）")
    parser.add_argument("--source", "-s", help="指定源网站类型 (amazon_us, amazon_jp, jd, dangdang, douban)")
    parser.add_argument("--output", "-o", help="结果输出HTML文件路径")
    parser.add_argument("--no-browser", "-n", action="store_true", help="不自动打开浏览器")
    
    args = parser.parse_args()
    
    try:
        # 读取HTML文件
        html_content = read_html_file(args.file)
        if not html_content:
            return 1
        
        # 测试选择器
        selector_result = test_selector(html_content, args.selector, args.attr, args.source)
        
        # 打印结果
        print(json.dumps(selector_result, ensure_ascii=False, indent=2))
        
        # 生成HTML报告
        report_file = generate_html_report(selector_result, html_content, args.output)
        
        # 自动打开浏览器查看结果（除非禁用）
        if not args.no_browser:
            report_url = f"file://{os.path.abspath(report_file)}"
            webbrowser.open(report_url)
        
        logger.info(f"选择器测试完成，匹配到 {selector_result.get('count', 0)} 个元素")
        
    except Exception as e:
        logger.error(f"测试选择器时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 