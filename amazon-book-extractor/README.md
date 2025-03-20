# 多源图书信息提取器

本项目提供一个强大的多源图书信息提取框架，支持从不同网站提取图书信息，包括亚马逊(美国、日本、英国)、京东、当当和豆瓣等。此外，还提供了丰富的选择器测试工具，帮助开发者快速验证和优化CSS选择器的提取效果。

## 主要功能

1. **多源提取框架**：支持从多个不同的网站提取图书信息
2. **插件式架构**：可轻松扩展支持新的网站来源
3. **选择器测试工具**：提供Python命令行和浏览器端两种测试工具
4. **源自动检测**：能够自动识别HTML内容的来源网站
5. **统一字段输出**：不同来源的数据被标准化为统一的字段格式

## 安装和依赖

本项目需要以下依赖：

```bash
pip install beautifulsoup4 requests
```

## 使用方法

### 多源提取器使用

```python
from multi_source_extractor import extract_book_info

# 从HTML文件提取图书信息
book_info = extract_book_info(file_path='path/to/your/html/file.html')

# 从HTML内容提取图书信息
with open('path/to/your/html/file.html', 'r', encoding='utf-8') as f:
    html_content = f.read()
book_info = extract_book_info(html_content=html_content, url='https://www.example.com/book/123')

# 批量处理目录中的HTML文件
from multi_source_extractor import batch_process_directory
results = batch_process_directory('path/to/your/html/directory')
```

### 命令行使用

```bash
# 处理单个文件
python multi_source_extractor.py --file path/to/your/html/file.html --output results.json

# 批量处理目录
python multi_source_extractor.py --dir path/to/your/html/directory --output results.json

# 测试选择器
python multi_source_extractor.py --file path/to/your/html/file.html --test-selector ".book-title" --attr "text"
```

### 选择器测试工具使用

#### Python命令行版

```bash
python test_selector.py path/to/your/html/file.html ".book-title" --attr "text" --source "amazon_us"
```

这将测试选择器 `.book-title` 在指定HTML文件上的效果，提取文本内容，并指定来源为亚马逊美国。测试结果会在终端输出，同时生成一个HTML报告并自动打开。

#### 浏览器版

1. 在浏览器中打开 `js_selector_test.html` 文件
2. 在页面上输入CSS选择器和HTML内容（或提供URL）
3. 点击"测试选择器"按钮
4. 查看匹配结果和实时预览

## 支持的网站

目前支持的网站及其对应的源名称：

| 网站 | 源名称 |
|------|--------|
| 亚马逊美国 | amazon_us |
| 亚马逊日本 | amazon_jp |
| 京东 | jd |
| 当当 | dangdang |
| 豆瓣 | douban |

## 提取的字段

对于所有来源，我们尝试提取以下统一字段：

- 书名
- 书本页面URL
- 作者
- 作者页面URL
- 作者简介
- 内容简介
- 出版时间
- 出版社
- ISBN
- 封面图片URL
- 评分
- 关联图书
- 读者评论

## 扩展支持新的网站源

要添加对新网站的支持，您需要：

1. 在 `multi_source_extractor.py` 中定义检测函数和提取函数
2. 注册这些函数到提取器注册表

示例：

```python
def is_new_source(html_content, url=""):
    """检测是否为新网站源"""
    return "new-source.com" in url.lower() or "new-source" in html_content.lower()

def extract_from_new_source(html_content, url=""):
    """从新网站源提取书籍信息"""
    book_info = {field: "" for field in BOOK_FIELDS}
    
    # 提取逻辑...
    
    return book_info

# 注册新网站源
registry.register_source_detector("new_source", is_new_source)
registry.register_extractor("new_source", extract_from_new_source)
registry.register_selector_tester("new_source", test_selector_generic)
```

## 贡献

欢迎提交问题报告和改进建议。如果您想贡献代码，请先创建一个问题讨论您的想法。

## 许可

本项目采用MIT许可证。
