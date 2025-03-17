#!/bin/bash

# 安装chardet库（如果需要）
pip install chardet

# 输出调试信息
echo "正在启动Amazon Book Extractor服务..."
echo "当前工作目录: $(pwd)"
echo "目录内容: $(ls -la)"

# 创建必要的目录
mkdir -p /app/data/html
mkdir -p /app/data/json
mkdir -p /app/data/markdown

# 设置环境变量
export PORT=${PORT:-8080}
export SAVE_DIRECTORY=${SAVE_DIRECTORY:-/app/data}
export CLOUD_DEPLOYMENT=true

echo "使用端口: $PORT"
echo "保存目录: $SAVE_DIRECTORY"

# 创建简单的服务状态页面
cat > service_status.html << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Amazon Book Extractor - 服务状态</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .status { padding: 20px; background-color: #f0f8ff; border-radius: 5px; }
        .running { color: green; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Amazon Book Extractor - 服务状态</h1>
        <div class="status">
            <h2>状态: <span class="running">运行中</span></h2>
            <p>保存目录: $SAVE_DIRECTORY</p>
            <p>时间戳: $(date -u +"%Y-%m-%dT%H:%M:%SZ")</p>
        </div>
    </div>
</body>
</html>
EOF

echo "服务状态页面已创建"

# 使用gunicorn启动应用
echo "正在启动gunicorn服务器..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 --access-logfile - --error-logfile - "local_service:app"
