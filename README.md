# The Brain书籍导入工具

本工具可以自动将从不同网站(亚马逊/京东/当当/豆瓣)提取的书籍信息导入到TheBrain应用中。

## 功能特点

- 从多个来源提取书籍数据
- 自动处理并转换成标准格式
- 自动创建TheBrain中的思想(Thought)
- 将书籍信息作为笔记(Note)添加到思想中
- 支持飞书集成通知

## 系统组件

本系统主要由以下部分组成:

1. **本地服务(local_service.py)**: 
   - 接收和处理来自浏览器扩展的数据
   - 支持同时发送到飞书和TheBrain

2. **TheBrain导入模块(auto_brain_importer.py)**:
   - 处理书籍数据并导入到TheBrain
   - 自动移除标题和YAML前置数据
   - 保留封面图片

3. **API交互模块(brain_importer.py)**:
   - 处理与TheBrain API的通信
   - 支持创建思想和更新笔记

## 安装和配置

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 默认配置信息存储在各模块内:
   - **Brain ID**: 53d07455-e094-44a5-a29b-82e0314abed1
   - **API Key**: 720f806f2855fd97727b2677e2b0b33935895ed1645260a9f58576644e2bc804
   - **Source Thought ID**: d9bb8a54-cfec-4ed4-986a-ae1c53471207

## 使用方法

### 运行本地服务

```bash
cd amazon-book-extractor
python local_service.py --port 5001 --directory "/path/to/save/files" [--webhook WEBHOOK_URL]
```

本地服务会接收浏览器扩展发送的书籍数据，并自动:
1. 保存书籍数据到本地文件
2. 生成JSON和Markdown文件
3. 发送数据到飞书(如配置)
4. 导入数据到TheBrain

### 手动导入JSON文件

如果需要单独导入已有的JSON文件:

```bash
cd /Users/wangxiaohui/Downloads/books_base
python auto_brain_importer.py /path/to/your/book.json
```

## 自定义

如果需要修改Brain ID或API密钥，请编辑以下文件中的配置变量:
- `/Users/wangxiaohui/Downloads/books_base/auto_brain_importer.py`

## 日志文件

系统会生成以下日志文件:
- `books_base/auto_importer.log` - 自动导入日志
- `books_base/brain_importer.log` - Brain API交互日志
- `amazon-book-extractor/local_service.log` - 本地服务日志
- `amazon-book-extractor/amazon_book_processor.log` - 亚马逊处理日志 