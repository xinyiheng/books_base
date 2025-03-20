#!/usr/bin/env python3
"""
多源图书信息提取器
支持从不同的网站源(亚马逊、当当、京东、豆瓣等)提取图书信息
支持插件式扩展提取源和测试提取效果
"""

import os
import re
import json
import logging
import traceback
import importlib
import inspect
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MultiSourceExtractor")

# 定义要提取的通用字段
BOOK_FIELDS = [
    "书名", "书本页面", "作者", "作者页面", "作者简介", 
    "内容简介", "出版时间", "出版社", "ISBN", "封面", 
    "评分", "关联图书", "读者评论"
]

class ExtractorRegistry:
    """提取器注册表，管理所有来源的提取器"""
    
    def __init__(self):
        self.source_detectors = {}  # 来源检测函数映射
        self.extractors = {}        # 提取器函数映射
        self.selector_testers = {}  # 选择器测试函数映射
        self.source_priorities = {} # 来源优先级映射
    
    def register_source_detector(self, source_name, detector_func, priority=10):
        """注册一个来源检测函数"""
        self.source_detectors[source_name] = detector_func
        self.source_priorities[source_name] = priority
        logger.info(f"已注册来源检测器: {source_name} (优先级: {priority})")
    
    def register_extractor(self, source_name, extractor_func):
        """注册一个提取器函数"""
        self.extractors[source_name] = extractor_func
        logger.info(f"已注册提取器: {source_name}")
    
    def register_selector_tester(self, source_name, tester_func):
        """注册一个选择器测试函数"""
        self.selector_testers[source_name] = tester_func
        logger.info(f"已注册选择器测试器: {source_name}")
    
    def detect_source(self, html_content, url=""):
        """检测HTML内容的来源，按优先级排序"""
        # 按优先级排序源检测器
        sorted_sources = sorted(
            self.source_detectors.keys(),
            key=lambda source: self.source_priorities.get(source, 10),
            reverse=True  # 优先级高的排在前面
        )
        
        # 按优先级检测
        for source_name in sorted_sources:
            detector = self.source_detectors[source_name]
            if detector(html_content, url):
                logger.info(f"检测到来源: {source_name} (优先级: {self.source_priorities.get(source_name, 10)})")
                return source_name
        
        logger.warning("无法识别HTML来源")
        return "unknown"
    
    def extract(self, source_name, html_content, url=""):
        """根据来源提取书籍信息"""
        if source_name in self.extractors:
            logger.info(f"使用 {source_name} 提取器提取书籍信息")
            return self.extractors[source_name](html_content, url)
        else:
            logger.error(f"未找到 {source_name} 的提取器")
            return {field: "" for field in BOOK_FIELDS}
    
    def test_selector(self, source_name, html_content, selector, attr=None):
        """测试选择器在特定来源上的效果"""
        if source_name in self.selector_testers:
            logger.info(f"测试 {source_name} 的选择器: {selector}")
            return self.selector_testers[source_name](html_content, selector, attr)
        else:
            logger.error(f"未找到 {source_name} 的选择器测试器")
            return {"error": f"未找到 {source_name} 的选择器测试器"}


# 创建全局注册表实例
registry = ExtractorRegistry()


# ---------- 亚马逊美国站点 ----------
def is_amazon_us(html_content, url=""):
    """检测是否为亚马逊美国站点"""
    url_check = "amazon.com" in url.lower()
    html_check = "amazon.com" in html_content.lower()
    title_check = False
    
    # 检查标题
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
    if title_match:
        title = title_match.group(1).lower()
        title_check = "amazon.com" in title or "amazon" in title and "united states" in html_content.lower()
    
    return url_check or html_check or title_check

def extract_from_amazon_us(html_content, url=""):
    """从亚马逊美国站点提取书籍信息"""
    # 这里可以调用现有的 amazon_feishu_extractor.py 中的 extract_us_book_info 函数
    # 也可以直接实现提取逻辑
    try:
        # 导入现有的提取函数
        from amazon_feishu_extractor import extract_us_book_info
        
        # 调用提取函数
        book_info = extract_us_book_info(html_content, base_url="https://www.amazon.com")
        
        # 确保返回的字段名符合 BOOK_FIELDS 的规范
        standardized_info = {field: "" for field in BOOK_FIELDS}
        
        # 映射字段
        field_mapping = {
            "title": "书名",
            "book_url": "书本页面",
            "author": "作者",
            "author_url": "作者页面",
            "author_bio": "作者简介",
            "description": "内容简介",
            "publication_date": "出版时间",
            "publisher": "出版社",
            "isbn": "ISBN",
            "cover_image_url": "封面",
            "amazon_rating": "评分",
            "related_books": "关联图书",
            "reviews": "读者评论"
        }
        
        # 填充标准化的信息
        for src_field, dst_field in field_mapping.items():
            if src_field in book_info and book_info[src_field]:
                standardized_info[dst_field] = book_info[src_field]
        
        return standardized_info
        
    except Exception as e:
        logger.error(f"从亚马逊美国提取信息时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return {field: "" for field in BOOK_FIELDS}

def test_selector_amazon_us(html_content, selector, attr=None):
    """测试选择器在亚马逊美国站点上的效果"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        elements = soup.select(selector)
        
        results = []
        for i, element in enumerate(elements[:5]):  # 最多返回5个结果
            if attr:
                if attr == "text":
                    results.append({"index": i, "content": element.get_text().strip()})
                elif element.has_attr(attr):
                    results.append({"index": i, "content": element[attr]})
                else:
                    results.append({"index": i, "content": f"元素不包含属性 {attr}"})
            else:
                results.append({"index": i, "content": element.get_text().strip()})
        
        return {
            "selector": selector,
            "attribute": attr,
            "count": len(elements),
            "results": results
        }
    except Exception as e:
        return {
            "selector": selector,
            "attribute": attr,
            "error": str(e)
        }

# 注册亚马逊美国站点的提取器
registry.register_source_detector("amazon_us", is_amazon_us)
registry.register_extractor("amazon_us", extract_from_amazon_us)
registry.register_selector_tester("amazon_us", test_selector_amazon_us)


# ---------- 亚马逊日本站点 ----------
def is_amazon_jp(html_content, url=""):
    """检测是否为亚马逊日本站点"""
    url_check = "amazon.co.jp" in url.lower()
    html_check = "amazon.co.jp" in html_content.lower()
    japan_check = "japan" in html_content.lower() or "日本" in html_content
    
    return url_check or html_check or japan_check

def extract_from_amazon_jp(html_content, url=""):
    """从亚马逊日本站点提取书籍信息"""
    try:
        # 导入现有的提取函数
        from amazon_feishu_extractor import extract_jp_book_info
        
        # 调用提取函数
        book_info = extract_jp_book_info(html_content, base_url="https://www.amazon.co.jp")
        
        # 确保返回的字段名符合 BOOK_FIELDS 的规范
        standardized_info = {field: "" for field in BOOK_FIELDS}
        
        # 映射字段
        field_mapping = {
            "title": "书名",
            "book_url": "书本页面",
            "author": "作者",
            "author_url": "作者页面",
            "author_bio": "作者简介",
            "description": "内容简介",
            "publication_date": "出版时间",
            "publisher": "出版社",
            "isbn": "ISBN",
            "cover_image_url": "封面",
            "amazon_rating": "评分",
            "related_books": "关联图书",
            "reviews": "读者评论"
        }
        
        # 填充标准化的信息
        for src_field, dst_field in field_mapping.items():
            if src_field in book_info and book_info[src_field]:
                standardized_info[dst_field] = book_info[src_field]
        
        return standardized_info
        
    except Exception as e:
        logger.error(f"从亚马逊日本提取信息时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return {field: "" for field in BOOK_FIELDS}

def test_selector_amazon_jp(html_content, selector, attr=None):
    """测试选择器在亚马逊日本站点上的效果"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        elements = soup.select(selector)
        
        results = []
        for i, element in enumerate(elements[:5]):
            if attr:
                if attr == "text":
                    results.append({"index": i, "content": element.get_text().strip()})
                elif element.has_attr(attr):
                    results.append({"index": i, "content": element[attr]})
                else:
                    results.append({"index": i, "content": f"元素不包含属性 {attr}"})
            else:
                results.append({"index": i, "content": element.get_text().strip()})
        
        return {
            "selector": selector,
            "attribute": attr,
            "count": len(elements),
            "results": results
        }
    except Exception as e:
        return {
            "selector": selector,
            "attribute": attr,
            "error": str(e)
        }

# 注册亚马逊日本站点的提取器
registry.register_source_detector("amazon_jp", is_amazon_jp, priority=5)
registry.register_extractor("amazon_jp", extract_from_amazon_jp)
registry.register_selector_tester("amazon_jp", test_selector_amazon_jp)


# ---------- 导入现有的提取器 ----------
def import_extractors_from_book_extractor_test():
    """从 book_extractor_test.py 导入提取器"""
    try:
        # 导入现有的提取器模块
        import book_extractor_test
        
        # 注册京东提取器
        registry.register_source_detector("jd", lambda html, url: book_extractor_test.detect_source(html) == "jd")
        registry.register_extractor("jd", book_extractor_test.extract_from_jd)
        registry.register_selector_tester("jd", test_selector_generic)
        
        # 注册当当提取器
        registry.register_source_detector("dangdang", lambda html, url: book_extractor_test.detect_source(html) == "dangdang")
        registry.register_extractor("dangdang", book_extractor_test.extract_from_dangdang)
        registry.register_selector_tester("dangdang", test_selector_generic)
        
        # 注册豆瓣提取器
        registry.register_source_detector("douban", lambda html, url: book_extractor_test.detect_source(html) == "douban")
        registry.register_extractor("douban", book_extractor_test.extract_from_douban)
        registry.register_selector_tester("douban", test_selector_generic)
        
        logger.info("成功导入现有提取器")
    except Exception as e:
        logger.error(f"导入现有提取器时出错: {str(e)}")
        logger.error(traceback.format_exc())

def test_selector_generic(html_content, selector, attr=None):
    """通用的选择器测试函数"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        elements = soup.select(selector)
        
        results = []
        for i, element in enumerate(elements[:5]):
            if attr:
                if attr == "text":
                    results.append({"index": i, "content": element.get_text().strip()})
                elif element.has_attr(attr):
                    results.append({"index": i, "content": element[attr]})
                else:
                    results.append({"index": i, "content": f"元素不包含属性 {attr}"})
            else:
                results.append({"index": i, "content": element.get_text().strip()})
        
        return {
            "selector": selector,
            "attribute": attr,
            "count": len(elements),
            "results": results
        }
    except Exception as e:
        return {
            "selector": selector,
            "attribute": attr,
            "error": str(e)
        }

# 导入现有提取器
import_extractors_from_book_extractor_test()


# ---------- 修复豆瓣来源检测 ----------
def is_douban(html_content, url=""):
    """
    检测是否为豆瓣图书页面
    使用更精确的检测方法
    """
    # 引入专门的豆瓣提取器
    from douban_extractor import is_douban_page
    return is_douban_page(html_content, url)

# 更新豆瓣源的注册代码 - 设置更高的优先级(20)
registry.register_source_detector("douban", is_douban, priority=20)

# 更新豆瓣提取器
def extract_from_douban_updated(html_content, url=""):
    """
    使用更新的豆瓣提取器提取图书信息
    """
    # 引入专门的豆瓣提取器
    from douban_extractor import extract_from_douban
    return extract_from_douban(html_content, url)

# 注册更新的豆瓣提取器
registry.register_extractor("douban", extract_from_douban_updated)


# ---------- 主要功能函数 ----------
def extract_book_info(file_path=None, html_content=None, url=""):
    """从HTML文件或内容中提取书籍信息"""
    if file_path:
        logger.info(f"处理文件: {file_path}")
        
        # 推断网页URL (如果未提供)
        if not url:
            filename = os.path.basename(file_path)
            if "京东" in filename or "jd" in filename.lower():
                url = "https://item.jd.com/book/"
            elif "当当" in filename or "dangdang" in filename.lower():
                url = "http://product.dangdang.com/book/"
            elif "豆瓣" in filename or "douban" in filename.lower():
                url = "https://book.douban.com/"
            elif "amazon" in filename.lower() and "jp" in filename.lower():
                url = "https://www.amazon.co.jp/"
            elif "amazon" in filename.lower() and "uk" in filename.lower():
                url = "https://www.amazon.co.uk/"
            elif "amazon" in filename.lower():
                url = "https://www.amazon.com/"
        
        try:
            # 尝试使用不同的编码方式读取文件
            encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1']
            html_content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        html_content = f.read()
                    logger.info(f"成功使用 {encoding} 编码读取文件")
                    break
                except UnicodeDecodeError:
                    continue
            
            if html_content is None:
                logger.error("无法使用任何编码读取文件")
                return {field: "" for field in BOOK_FIELDS}
        
        except Exception as e:
            logger.error(f"读取文件时出错: {str(e)}")
            logger.error(traceback.format_exc())
            return {field: "" for field in BOOK_FIELDS}
    
    if not html_content:
        logger.error("未提供HTML内容")
        return {field: "" for field in BOOK_FIELDS}
    
    try:
        # 检测来源
        source = registry.detect_source(html_content, url)
        
        # 如果无法识别来源，尝试所有提取器
        if source == "unknown":
            logger.warning(f"无法识别HTML来源，尝试所有提取器")
            
            results = {}
            for source_name, extractor in registry.extractors.items():
                logger.info(f"尝试使用 {source_name} 提取器")
                results[source_name] = extractor(html_content, url)
            
            # 计算每个结果中有多少非空字段
            filled_fields = {
                source_name: sum(1 for value in info.values() if value) 
                for source_name, info in results.items()
            }
            
            # 选择非空字段最多的结果
            best_source = max(filled_fields, key=filled_fields.get)
            logger.info(f"选择最佳结果来源: {best_source}, 填充了 {filled_fields[best_source]} 个字段")
            return results[best_source]
        else:
            # 使用检测到的来源提取信息
            return registry.extract(source, html_content, url)
    
    except Exception as e:
        logger.error(f"提取信息时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return {field: "" for field in BOOK_FIELDS}

def test_selector(html_content, selector, attr=None, source=None):
    """测试选择器在HTML上的效果"""
    if not html_content:
        return {"error": "未提供HTML内容"}
    
    try:
        # 如果未指定来源，检测来源
        if not source:
            source = registry.detect_source(html_content)
        
        # 如果仍然无法识别来源或来源不在注册表中，使用通用测试器
        if source == "unknown" or source not in registry.selector_testers:
            logger.warning(f"未知来源或来源不在注册表中: {source}，使用通用测试器")
            return test_selector_generic(html_content, selector, attr)
        
        # 使用特定来源的测试器
        return registry.selector_testers[source](html_content, selector, attr)
    
    except Exception as e:
        logger.error(f"测试选择器时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "selector": selector,
            "attribute": attr,
            "error": str(e)
        }

def batch_process_directory(directory, output_file=None):
    """批量处理目录中的所有HTML文件"""
    if not os.path.isdir(directory):
        logger.error(f"目录不存在: {directory}")
        return {}
    
    logger.info(f"开始处理目录: {directory}")
    results = {}
    
    # 处理目录中的所有HTML文件
    for filename in os.listdir(directory):
        if filename.endswith(".html") or filename.endswith(".htm"):
            file_path = os.path.join(directory, filename)
            logger.info(f"===== 开始处理文件: {filename} =====")
            
            # 提取书籍信息
            book_info = extract_book_info(file_path=file_path)
            
            # 将结果保存到字典
            results[filename] = book_info
            
            logger.info(f"===== 处理完成: {filename} =====\n")
    
    # 将结果保存到JSON文件
    if output_file:
        output_path = output_file
    else:
        output_path = os.path.join(directory, "extraction_results.json")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"结果已保存到: {output_path}")
    
    # 打印摘要
    logger.info(f"成功处理了 {len(results)} 个文件")
    for filename, info in results.items():
        filled_fields = sum(1 for value in info.values() if value)
        total_fields = len(BOOK_FIELDS)
        logger.info(f"{filename}: 填充了 {filled_fields}/{total_fields} 个字段")
    
    return results

def process_single_file(file_path, output_file=None):
    """处理单个HTML文件并返回结果"""
    if not os.path.isfile(file_path):
        logger.error(f"文件不存在: {file_path}")
        return {}
    
    logger.info(f"处理文件: {file_path}")
    book_info = extract_book_info(file_path=file_path)
    
    # 将结果保存到JSON文件
    if output_file:
        directory = os.path.dirname(output_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(book_info, f, ensure_ascii=False, indent=2)
        
        logger.info(f"结果已保存到: {output_file}")
    
    # 打印摘要
    filled_fields = sum(1 for value in book_info.values() if value)
    total_fields = len(BOOK_FIELDS)
    logger.info(f"填充了 {filled_fields}/{total_fields} 个字段")
    
    return book_info

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="多源图书信息提取器")
    parser.add_argument("--file", "-f", help="要处理的HTML文件路径")
    parser.add_argument("--dir", "-d", help="要处理的HTML文件目录")
    parser.add_argument("--output", "-o", help="结果输出文件路径")
    parser.add_argument("--test-selector", "-t", help="测试CSS选择器")
    parser.add_argument("--attr", "-a", help="测试选择器时，要提取的属性（默认为文本）")
    parser.add_argument("--source", "-s", help="指定来源（用于测试选择器）")
    
    args = parser.parse_args()
    
    if args.test_selector:
        if not args.file:
            logger.error("测试选择器需要指定HTML文件")
            return
        
        # 读取HTML文件
        try:
            encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1']
            html_content = None
            
            for encoding in encodings:
                try:
                    with open(args.file, 'r', encoding=encoding) as f:
                        html_content = f.read()
                    logger.info(f"成功使用 {encoding} 编码读取文件")
                    break
                except UnicodeDecodeError:
                    continue
            
            if html_content is None:
                logger.error("无法使用任何编码读取文件")
                return
            
            # 测试选择器
            result = test_selector(html_content, args.test_selector, args.attr, args.source)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        except Exception as e:
            logger.error(f"测试选择器时出错: {str(e)}")
            logger.error(traceback.format_exc())
    
    elif args.file:
        # 处理单个文件
        process_single_file(args.file, args.output)
    
    elif args.dir:
        # 批量处理目录
        batch_process_directory(args.dir, args.output)
    
    else:
        logger.error("请指定要处理的文件或目录")

if __name__ == "__main__":
    main() 