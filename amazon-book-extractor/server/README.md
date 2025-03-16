# Amazon Book Extractor 云服务部署指南

这个目录包含了Amazon Book Extractor的服务端代码，可以部署到Zeabur等云平台上，以便浏览器插件可以直接连接云服务，无需在本地运行服务。

## 部署步骤

### 1. 准备工作

1. 将本地服务代码复制到server目录中：
   ```
   cp ../local_service.py ./
   cp ../process_amazon_book.py ./
   cp ../feishu_webhook.py ./
   cp ../json_to_markdown.py ./
   ```

2. 创建一个GitHub仓库，并将代码推送到仓库中

### 2. 在Zeabur上部署

1. 注册并登录[Zeabur](https://zeabur.com)
2. 创建一个新项目
3. 选择"从GitHub导入"，并连接您的GitHub仓库
4. 选择server目录作为部署目录
5. Zeabur会自动检测到Dockerfile并构建应用
6. 部署完成后，Zeabur会提供一个域名，例如`https://amazon-book-extractor.zeabur.app`

### 3. 配置持久化存储

为了确保数据不会在容器重启后丢失，请配置Zeabur的持久化卷：

1. 在Zeabur控制台中，打开您部署的服务页面
2. 点击"硬盘"标签，然后点击"Mount Volumes"按钮
3. 设置Volume ID为`book-data`（或您喜欢的名称）
4. 设置Mount Directory为`/app/data`
5. 点击确认挂载

这样配置后，即使容器重启，您的数据也会被保留。

### 4. 配置浏览器插件

1. 打开浏览器插件的设置页面
2. 在"云服务"部分，启用"启用云服务"选项
3. 在"云服务URL"中输入Zeabur提供的域名
4. 点击"测试连接"确保连接成功
5. 保存设置

### 5. 数据同步功能

新增的数据同步功能允许您在本地和云端之间同步数据：

1. 在设置页面的"数据同步"部分，您可以：
   - 点击"从本地同步到云端"将本地数据上传到云端
   - 点击"从云端同步到本地"将云端数据下载到本地

2. 同步过程会比较文件修改时间，只同步较新的文件，避免覆盖更新的数据

## 环境变量配置

Zeabur会自动设置以下环境变量：

- `PORT`: 服务监听的端口，由Zeabur自动设置
- `SAVE_DIRECTORY`: 数据保存目录，设置为`/app/data`
- `CLOUD_DEPLOYMENT`: 标记为云部署环境，设置为`true`

## 数据存储

在云环境中，所有数据都存储在容器的`/app/data`目录中，包括：

- `/app/data/html`: HTML文件
- `/app/data/json`: JSON文件
- `/app/data/markdown`: Markdown文件

通过配置持久化卷，这些数据将被保存在Zeabur的持久存储中，即使容器重启也不会丢失。
