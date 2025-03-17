FROM python:3.9-slim

WORKDIR /app

# 复制服务端代码
COPY server/ .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# 创建必要的目录
RUN mkdir -p /app/data/html
RUN mkdir -p /app/data/json
RUN mkdir -p /app/data/markdown

# 设置环境变量
ENV PORT=8080
ENV SAVE_DIRECTORY=/app/data
ENV CLOUD_DEPLOYMENT=true

# 暴露端口
EXPOSE 8080

# 启动服务
CMD ["python", "local_service.py"]
