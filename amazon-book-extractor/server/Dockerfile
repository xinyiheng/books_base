FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装chardet库（如果需要）
RUN pip install chardet

# 安装gunicorn
RUN pip install gunicorn

# 创建必要的目录
RUN mkdir -p /app/data/html
RUN mkdir -p /app/data/json
RUN mkdir -p /app/data/markdown

# 复制服务端代码
COPY . .

# 设置启动脚本权限
RUN chmod +x start.sh

# 设置环境变量
ENV PORT=8080
ENV SAVE_DIRECTORY=/app/data
ENV CLOUD_DEPLOYMENT=true

# 创建卷挂载点
VOLUME ["/app/data"]

# 暴露端口
EXPOSE 8080

# 启动服务
CMD ["./start.sh"]
