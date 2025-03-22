# 在接收京东、当当或豆瓣数据的路由中，统一使用书名作为文件名
@app.route('/save-jd-data', methods=['POST', 'OPTIONS'])
def save_jd_data():
    """保存从JD/Dangdang/Douban提取的图书数据"""
    if request.method == 'OPTIONS':
        return build_cors_preflight_response()
    
    try:
        data = request.json
        filename = request.args.get('filename', '')
        
        if not data:
            logger.error("收到的数据为空")
            return make_response(jsonify({"error": "No data received"}), 400)
        
        # 获取数据来源域名
        domain = data.get('domain', '')
        
        # 确定数据来源
        source = ""
        if "jd.com" in domain:
            source = "jd"
        elif "dangdang.com" in domain:
            source = "dangdang"
        elif "douban.com" in domain:
            source = "douban"
        else:
            source = "jd"  # 默认假设为京东
        
        # 使用书名作为文件名（如果有）
        title = data.get('标题') or data.get('书名') or data.get('title', '')
        isbn = data.get('ISBN') or data.get('isbn', '')
        
        # 使用书名作为文件名（如果有）
        if title:
            # 限制长度
            if len(title) > 100:
                title = title[:100]
            
            base_filename = title
        elif isbn:
            # 如果没有书名但有ISBN，使用ISBN
            base_filename = f"书籍_{isbn}"
        else:
            # 如果提供了文件名参数，使用它
            if filename:
                base_filename = os.path.splitext(filename)[0]
            else:
                # 否则使用时间戳
                base_filename = f"{source}_book_unknown_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 添加时间戳，确保唯一性
        timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S-%f')[:-3] + 'Z'
        json_filename = f"{base_filename}_{timestamp}.json"
        
        # 构建完整的文件路径
        json_path = os.path.join(SAVE_DIR, 'json', json_filename)
        
        # 添加源信息和时间戳
        data['timestamp'] = timestamp
        data['source'] = source
        
        # 确保JSON目录存在
        os.makedirs(os.path.join(SAVE_DIR, 'json'), exist_ok=True)
        
        # 保存JSON文件
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存{source.upper()}图书数据: {json_path}")
        
        # 转换为Markdown（如果需要）
        try:
            from json_to_markdown import convert_to_markdown
            
            md_content = convert_to_markdown(data)
            md_filename = f"{base_filename}.md"
            md_path = os.path.join(SAVE_DIR, 'markdown', md_filename)
            
            # 确保Markdown目录存在
            os.makedirs(os.path.join(SAVE_DIR, 'markdown'), exist_ok=True)
            
            # 保存Markdown文件
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            logger.info(f"已生成Markdown文件: {md_path}")
        except Exception as e:
            logger.error(f"生成Markdown时出错: {str(e)}")
        
        # 保存HTML文件（如果有）
        html_content = data.get('html_content', '')
        if html_content:
            html_path = os.path.join(SAVE_DIR, 'html', f"{source}_book_{isbn or 'unknown'}_{base_filename}_{timestamp}.html")
            
            # 确保HTML目录存在
            os.makedirs(os.path.join(SAVE_DIR, 'html'), exist_ok=True)
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"已保存HTML源文件: {html_path}")
        
        return make_response(jsonify({"success": True, "message": "数据已保存", "path": json_path}), 200)
    
    except Exception as e:
        logger.error(f"保存数据时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return make_response(jsonify({"error": str(e)}), 500) 