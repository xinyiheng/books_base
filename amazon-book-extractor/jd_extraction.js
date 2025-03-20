/**
 * 京东图书信息提取脚本 - 专门从 p-name ac 提取关联图书
 */
(function() {
    // 创建用于存储提取信息的对象 (移除了原作名字段)
    const bookInfo = {
        "书名": "",
        "作者": "",
        "作者页面": "",
        "封面": "",
        "内容简介": "",
        "ISBN": "",
        "书本页面": "",
        "出版社": "",
        "出版时间": "",
        "评分": "",
        "关联图书": [],
        "读者评论": [],
        "region": "cn",
        "domain": "jd.com",
        "file_name": "",
        "processed_time": "",
        "url": ""
    };

    // 提取书名
    function extractTitle() {
        const titleElement = document.querySelector('.sku-name');
        if (titleElement) {
            bookInfo.书名 = titleElement.innerText.trim();
            console.log("提取到书名:", bookInfo.书名);
        }
    }

    // 提取页面URL
    function extractPageUrl() {
        const canonicalLink = document.querySelector('link[rel="canonical"]');
        if (canonicalLink) {
            const href = canonicalLink.getAttribute('href');
            bookInfo.书本页面 = href.startsWith('//') ? 'https:' + href : href;
        } else {
            bookInfo.书本页面 = window.location.href;
        }
        console.log("提取到页面URL:", bookInfo.书本页面);
    }

    // 提取作者信息
    function extractAuthor() {
        const authorElement = document.querySelector('.p-author');
        if (authorElement) {
            const authorLink = authorElement.querySelector('a');
            if (authorLink) {
                bookInfo.作者 = authorLink.textContent.trim();
                
                let authorUrl = authorLink.getAttribute('href');
                if (authorUrl) {
                    bookInfo.作者页面 = authorUrl.startsWith('//') ? 'https:' + authorUrl : authorUrl;
                }
            } else {
                bookInfo.作者 = authorElement.textContent.trim();
            }
            console.log("提取到作者:", bookInfo.作者);
        }
    }

    // 提取内容简介 - 只保留图片URL，去掉<p>标签
    function extractDescription() {
        const descElement = document.querySelector('.book-detail-content');
        if (descElement) {
            const imgElements = descElement.querySelectorAll('img');
            const imageUrls = [];
            
            imgElements.forEach(img => {
                let imgSrc = img.getAttribute('src') || img.getAttribute('data-lazyload');
                if (imgSrc) {
                    // 确保URL是完整的，如果以//开头，添加http:
                    if (imgSrc.startsWith('//')) {
                        imgSrc = 'http:' + imgSrc;
                    }
                    imageUrls.push(imgSrc);
                }
            });
            
            // 将所有图片URL连接为字符串
            bookInfo.内容简介 = imageUrls.join('\n');
            console.log("提取到内容简介URL");
        }
    }

    // 提取出版信息
    function extractPublishInfo() {
        const parameterList = document.querySelector('.parameter2.p-parameter-list');
        if (parameterList) {
            const items = parameterList.querySelectorAll('li');
            
            items.forEach(item => {
                const text = item.textContent.trim();
                
                if (text.includes('出版社：')) {
                    const publisherLink = item.querySelector('a');
                    if (publisherLink) {
                        bookInfo.出版社 = publisherLink.textContent.trim();
                    } else {
                        bookInfo.出版社 = text.replace('出版社：', '').trim();
                    }
                }
                
                if (text.includes('ISBN：')) {
                    bookInfo.ISBN = text.replace('ISBN：', '').trim();
                }
                
                if (text.includes('出版时间：')) {
                    bookInfo.出版时间 = text.replace('出版时间：', '').trim();
                }
            });
            console.log("提取到出版信息:", bookInfo.出版社, bookInfo.ISBN, bookInfo.出版时间);
        }
    }

    // 提取封面图片
    function extractCoverImage() {
        const imgElement = document.querySelector('#spec-img') || 
                          document.querySelector('.product-img img') || 
                          document.querySelector('.img-hover img');
        
        if (imgElement) {
            let imgSrc = imgElement.getAttribute('src') || imgElement.getAttribute('data-origin');
            if (imgSrc) {
                if (imgSrc.startsWith('//')) {
                    imgSrc = 'https:' + imgSrc;
                }
                bookInfo.封面 = imgSrc;
                console.log("提取到封面图片:", bookInfo.封面);
            }
        }
    }

    // 提取评分 - 从全部评价中提取
    function extractRating() {
        const ratingElement = document.querySelector('a[clstag*="allpingjia"]');
        if (ratingElement) {
            // 获取全部文本内容
            const fullText = ratingElement.textContent.trim();
            
            // 提取括号中的评价数量
            const ratingMatch = fullText.match(/\((.*?)\)/);
            if (ratingMatch && ratingMatch[1]) {
                bookInfo.评分 = ratingMatch[1].trim();
            } else {
                bookInfo.评分 = fullText;
            }
            
            console.log("提取到评分:", bookInfo.评分);
        }
    }

    // 专门从 p-name ac 提取关联图书
    function extractRelatedBooks() {
        console.log("开始从p-name ac提取关联图书...");
        
        // 直接查找所有 p-name ac 元素
        const pNameElements = document.querySelectorAll('.p-name.ac');
        
        if (pNameElements && pNameElements.length > 0) {
            console.log(`找到${pNameElements.length}个p-name ac元素`);
            
            pNameElements.forEach((nameDiv, index) => {
                const bookLink = nameDiv.querySelector('a');
                
                if (bookLink) {
                    // 获取标题和链接
                    const title = bookLink.getAttribute('title') || bookLink.textContent.trim();
                    let url = bookLink.getAttribute('href') || '';
                    
                    // 确保URL是完整的
                    if (url.startsWith('//')) {
                        url = 'https:' + url;
                    } else if (url.startsWith('/')) {
                        url = 'https://item.jd.com' + url;
                    }
                    
                    // 过滤无效和重复的链接
                    if (url && !url.includes('javascript:') && !url.includes('#') && 
                        !title.includes('全部评论') && !title.includes('晒图') && 
                        !title.includes('试用报告') && 
                        !bookInfo.关联图书.some(book => book.title === title)) {
                        
                        bookInfo.关联图书.push({
                            title: title,
                            url: url
                        });
                        console.log(`提取到关联图书${bookInfo.关联图书.length}: ${title}`);
                    }
                }
            });
            
            console.log(`成功提取了${bookInfo.关联图书.length}本关联图书`);
        } else {
            console.log("未找到p-name ac元素，尝试备用方法...");
            
            // 备用方法：查找任何包含图书列表的容器
            const containers = document.querySelectorAll('.mc');
            
            for (const container of containers) {
                const nameElements = container.querySelectorAll('.p-name');
                
                if (nameElements && nameElements.length > 0) {
                    console.log(`在MC容器中找到${nameElements.length}个p-name元素`);
                    
                    nameElements.forEach((nameDiv, index) => {
                        const bookLink = nameDiv.querySelector('a');
                        
                        if (bookLink) {
                            const title = bookLink.getAttribute('title') || bookLink.textContent.trim();
                            let url = bookLink.getAttribute('href') || '';
                            
                            if (url.startsWith('//')) {
                                url = 'https:' + url;
                            } else if (url.startsWith('/')) {
                                url = 'https://item.jd.com' + url;
                            }
                            
                            if (url && !url.includes('javascript:') && !url.includes('#') && 
                                !title.includes('全部评论') && !title.includes('晒图') && 
                                !title.includes('试用报告') && 
                                !bookInfo.关联图书.some(book => book.title === title)) {
                                
                                bookInfo.关联图书.push({
                                    title: title,
                                    url: url
                                });
                                console.log(`备用方法提取到关联图书: ${title}`);
                            }
                        }
                    });
                    
                    // 如果找到了足够的相关图书，就不再继续查找
                    if (bookInfo.关联图书.length > 0) break;
                }
            }
        }
        
        // 最后一次尝试：直接获取页面中所有合适的链接
        if (bookInfo.关联图书.length === 0) {
            console.log("使用最后的备用方法...");
            
            // 查找任何可能包含图书链接的元素
            document.querySelectorAll('a[title]').forEach(link => {
                const title = link.getAttribute('title');
                let url = link.getAttribute('href');
                
                if (title && url && !url.includes('javascript:') && !url.includes('#') && 
                    !title.includes('全部评论') && !title.includes('晒图') && !title.includes('试用报告')) {
                    
                    // 处理URL
                    if (url.startsWith('//')) {
                        url = 'https:' + url;
                    } else if (url.startsWith('/')) {
                        url = 'https://item.jd.com' + url;
                    }
                    
                    // 避免重复添加
                    if (!bookInfo.关联图书.some(book => book.title === title)) {
                        bookInfo.关联图书.push({
                            title: title,
                            url: url
                        });
                        console.log(`最后备用方法提取到关联图书: ${title}`);
                    }
                }
            });
        }
        
        console.log(`关联图书提取完成，共找到${bookInfo.关联图书.length}本`);
    }

    // 执行所有提取函数
    function extractAllInfo() {
        console.log("开始提取京东图书信息...");
        extractTitle();
        extractPageUrl();
        extractAuthor();
        extractDescription();
        extractPublishInfo();
        extractCoverImage();
        extractRating();
        extractRelatedBooks();
        
        // 添加时间戳和URL信息
        bookInfo.processed_time = new Date().toISOString().replace('T', ' ').substring(0, 19);
        bookInfo.url = window.location.href;
        bookInfo.file_name = `JD_Book_${bookInfo.书名 || bookInfo.ISBN || 'unknown'}.html`;
        
        // 输出结果 (以JSON格式)
        console.log("提取完成! 图书信息如下:");
        console.log(JSON.stringify(bookInfo, null, 2));
        
        // 自动发送到本地服务器
        sendToLocalServer(bookInfo);
        
        // 同时创建下载链接，以备本地服务器不可用时使用
        createDownloadLink(bookInfo);
        
        return bookInfo;
    }
    
    // 创建下载链接，允许用户保存提取的信息
    function createDownloadLink(data) {
        try {
            const jsonStr = JSON.stringify(data, null, 2);
            const blob = new Blob([jsonStr], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            
            // 移除可能已存在的下载链接
            const existingLink = document.getElementById('jd-book-extract-download');
            if (existingLink) {
                existingLink.remove();
            }
            
            // 创建下载按钮
            const downloadContainer = document.createElement('div');
            downloadContainer.style.position = 'fixed';
            downloadContainer.style.top = '50px';
            downloadContainer.style.right = '20px';
            downloadContainer.style.zIndex = '9999';
            downloadContainer.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
            downloadContainer.style.borderRadius = '5px';
            downloadContainer.style.backgroundColor = '#fff';
            downloadContainer.style.padding = '10px';
            
            // 创建标题
            const title = document.createElement('div');
            title.textContent = '图书信息提取完成';
            title.style.marginBottom = '10px';
            title.style.fontWeight = 'bold';
            title.style.color = '#e2231a';
            downloadContainer.appendChild(title);
            
            // 显示提取结果数量
            const statsInfo = document.createElement('div');
            statsInfo.textContent = `找到${data.关联图书.length}本关联图书`;
            statsInfo.style.marginBottom = '10px';
            statsInfo.style.fontSize = '12px';
            downloadContainer.appendChild(statsInfo);
            
            // 显示自动发送状态
            const autoSendInfo = document.createElement('div');
            autoSendInfo.textContent = '数据已自动发送到本地服务器(端口5001)';
            autoSendInfo.style.marginBottom = '10px';
            autoSendInfo.style.fontSize = '12px';
            autoSendInfo.style.color = '#2E8B57';
            downloadContainer.appendChild(autoSendInfo);
            
            // 创建下载链接
            const downloadLink = document.createElement('a');
            downloadLink.id = 'jd-book-extract-download';
            downloadLink.href = url;
            downloadLink.download = `${data.书名 || `JD_Book_${data.ISBN || 'unknown'}`}.json`;
            downloadLink.textContent = '点击下载JSON文件(备用)';
            downloadLink.style.display = 'block';
            downloadLink.style.padding = '8px 15px';
            downloadLink.style.backgroundColor = '#e2231a';
            downloadLink.style.color = 'white';
            downloadLink.style.borderRadius = '3px';
            downloadLink.style.textDecoration = 'none';
            downloadLink.style.textAlign = 'center';
            downloadLink.style.marginBottom = '5px';
            
            downloadLink.addEventListener('click', function() {
                console.log("下载文件中...");
                setTimeout(() => {
                    downloadContainer.style.display = 'none';
                }, 5000);
            });
            
            downloadContainer.appendChild(downloadLink);
            
            // 创建关闭按钮
            const closeButton = document.createElement('div');
            closeButton.textContent = '关闭';
            closeButton.style.textAlign = 'center';
            closeButton.style.cursor = 'pointer';
            closeButton.style.fontSize = '12px';
            closeButton.style.color = '#666';
            closeButton.addEventListener('click', function() {
                downloadContainer.style.display = 'none';
            });
            downloadContainer.appendChild(closeButton);
            
            // 添加到页面
            document.body.appendChild(downloadContainer);
            console.log("下载链接已创建，数据已自动发送到本地服务器");
            
            // 5秒后自动关闭提示
            setTimeout(() => {
                downloadContainer.style.display = 'none';
            }, 5000);
        } catch (error) {
            console.error("创建下载链接失败:", error);
        }
    }
    
    function sendToLocalServer(data) {
        // 使用本地服务器的地址和端口5001
        const serverUrl = 'http://localhost:5001/save-jd-data';
        
        // 准备要发送的数据（保持与亚马逊格式一致）
        const jsonData = JSON.stringify(data, null, 2);
        const filename = `${data.书名 || `JD_Book_${data.ISBN || 'unknown'}`}.json`;
        
        console.log("正在发送数据到本地服务器...");
        
        // 使用fetch API发送数据
        fetch(serverUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                filename: filename,
                data: jsonData,
                source: 'jd',
                url: window.location.href,
                timestamp: new Date().toISOString()
            })
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('网络响应不正常');
        })
        .then(result => {
            console.log('数据成功发送到本地服务器:', result);
            // 不再显示成功提示，因为已在UI中显示
        })
        .catch(error => {
            console.error('发送数据到本地服务器失败:', error);
            // 在下载容器中显示错误信息
            const errorDiv = document.createElement('div');
            errorDiv.textContent = `服务器连接失败: ${error.message}`;
            errorDiv.style.color = 'red';
            errorDiv.style.fontSize = '12px';
            errorDiv.style.marginBottom = '10px';
            
            const downloadContainer = document.querySelector('#jd-book-extract-download').parentNode;
            if (downloadContainer) {
                downloadContainer.insertBefore(errorDiv, downloadContainer.querySelector('a'));
                // 移除自动发送成功的信息
                const autoSendInfo = downloadContainer.querySelector('div:nth-child(3)');
                if (autoSendInfo) {
                    autoSendInfo.textContent = '自动发送失败，请手动下载';
                    autoSendInfo.style.color = 'red';
                }
            }
        });
    }
    
    // 执行提取流程
    return extractAllInfo();
})();