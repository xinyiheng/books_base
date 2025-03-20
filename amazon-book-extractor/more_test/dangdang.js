/**
 * 当当网图书信息提取脚本
 * 自动提取图书信息并发送到本地服务器(端口5001)
 */
(function() {
    // 创建用于存储提取信息的对象 (与亚马逊格式保持一致)
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
        "domain": "dangdang.com",
        "file_name": "",
        "processed_time": "",
        "url": ""
    };

    // 辅助函数：查找包含特定文本的元素
    function findElementContainingText(selector, text) {
        const elements = document.querySelectorAll(selector);
        for (let i = 0; i < elements.length; i++) {
            if (elements[i].textContent.includes(text)) {
                return elements[i];
            }
        }
        return null;
    }

    // 提取书名
    function extractTitle() {
        const titleElement = document.querySelector('h1[title]');
        if (titleElement) {
            bookInfo.书名 = titleElement.getAttribute('title') || titleElement.innerText.trim();
            console.log("提取到书名:", bookInfo.书名);
        }
    }

    // 提取页面URL
    function extractPageUrl() {
        // 先尝试从规范链接获取
        const canonicalLink = document.querySelector('link[rel="canonical"]');
        if (canonicalLink) {
            const href = canonicalLink.getAttribute('href');
            // 处理相对路径
            if (href && href.startsWith('/')) {
                bookInfo.书本页面 = 'https://product.dangdang.com' + href;
            } else {
                bookInfo.书本页面 = href;
            }
        } 
        
        // 如果没有找到规范链接，使用当前页面URL
        if (!bookInfo.书本页面) {
            bookInfo.书本页面 = window.location.href;
        }
        
        console.log("提取到页面URL:", bookInfo.书本页面);
    }

    // 提取作者信息
    function extractAuthor() {
        const authorElement = document.querySelector('#author');
        if (authorElement) {
            const authorLink = authorElement.querySelector('a');
            if (authorLink) {
                bookInfo.作者 = authorLink.textContent.trim();
                bookInfo.作者页面 = authorLink.getAttribute('href');
                // 确保URL是完整的
                if (bookInfo.作者页面 && bookInfo.作者页面.startsWith('http')) {
                    // URL已经是完整的，无需处理
                } else if (bookInfo.作者页面) {
                    // 添加前缀
                    bookInfo.作者页面 = 'http:' + bookInfo.作者页面;
                }
                console.log("提取到作者:", bookInfo.作者);
            }
        }
    }

    // 提取作者简介
    function extractAuthorIntro() {
        const authorIntroElement = document.querySelector('#authorIntroduction');
        if (authorIntroElement) {
            const descrip = authorIntroElement.querySelector('.descrip');
            if (descrip) {
                // 移除所有HTML标签
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = descrip.innerHTML;
                const textContent = tempDiv.textContent.trim();
                bookInfo.作者简介 = textContent;
                console.log("提取到作者简介");
            }
        }
    }

    // 提取内容简介 - 合并多个来源
    function extractDescription() {
        let descriptions = {};
        console.log("开始提取内容简介...");
        
        // 打印页面中的相关元素，以便调试
        console.log("feature-all元素存在:", document.getElementById('feature-all') ? "是" : "否");
        console.log("abstract-all元素存在:", document.getElementById('abstract-all') ? "是" : "否");
        console.log("content-all元素存在:", document.getElementById('content-all') ? "是" : "否");
        
        // 使用document.querySelector也试一下
        console.log("使用querySelector查找feature-all:", document.querySelector('#feature-all') ? "找到" : "未找到");
        console.log("使用querySelector查找abstract-all:", document.querySelector('#abstract-all') ? "找到" : "未找到");
        console.log("使用querySelector查找content-all:", document.querySelector('#content-all') ? "找到" : "未找到");
        
        // 尝试使用更广泛的选择器来查找内容
        const descriptionContainers = document.querySelectorAll('div.descrip');
        console.log(`找到${descriptionContainers.length}个descrip容器`);
        
        // 提取feature-all部分的图片 (尝试多种选择器)
        let featureElement = document.getElementById('feature-all') || 
                          document.querySelector('#feature-all') ||
                          document.querySelector('span#feature-all');
        
        // 如果直接找不到feature-all，尝试找包含它的div.descrip
        if (!featureElement) {
            descriptionContainers.forEach((container, index) => {
                if (container.querySelector('#feature-all') || container.innerHTML.includes('feature-all')) {
                    console.log(`在第${index + 1}个descrip容器中找到feature-all`);
                    featureElement = container;
                }
            });
        }
        
        if (featureElement) {
            console.log("找到feature-all元素:", featureElement);
            // 提取所有图片URL
            const imgElements = featureElement.querySelectorAll('img');
            console.log(`feature-all中找到${imgElements.length}个图片元素`);
            
            const featureImages = [];
            imgElements.forEach(img => {
                let imgSrc = img.getAttribute('src');
                console.log("发现图片URL:", imgSrc);
                if (imgSrc) {
                    if (!imgSrc.startsWith('http')) {
                        imgSrc = 'http:' + imgSrc;
                    }
                    featureImages.push(imgSrc);
                }
            });
            if (featureImages.length > 0) {
                descriptions.feature = featureImages;
                console.log("提取到feature-all图片:", featureImages);
            }
        } else {
            console.log("找不到feature-all元素");
        }
        
        // 提取abstract-all文本内容 (尝试多种选择器)
        let abstractElement = document.getElementById('abstract-all') || 
                           document.querySelector('#abstract-all') ||
                           document.querySelector('span#abstract-all');
        
        // 如果直接找不到abstract-all，尝试找包含它的div.descrip
        if (!abstractElement) {
            descriptionContainers.forEach((container, index) => {
                if (container.querySelector('#abstract-all') || container.innerHTML.includes('abstract-all')) {
                    console.log(`在第${index + 1}个descrip容器中找到abstract-all`);
                    abstractElement = container;
                }
            });
        }
        
        if (abstractElement) {
            console.log("找到abstract-all元素:", abstractElement);
            // 使用innerHTML查看原始内容进行调试
            console.log("abstract-all原始HTML:", abstractElement.innerHTML);
            
            const paragraphs = abstractElement.querySelectorAll('p');
            console.log(`abstract-all中找到${paragraphs.length}个段落`);
            
            let abstractText = '';
            paragraphs.forEach(p => {
                if (!p.querySelector('img')) { // 跳过只包含图片的段落
                    abstractText += p.textContent.trim() + '\n';
                }
            });
            
            // 如果没找到段落，尝试直接获取文本内容
            if (!abstractText && abstractElement.textContent) {
                abstractText = abstractElement.textContent.trim();
            }
            
            if (abstractText) {
                descriptions.abstract = abstractText.trim();
                console.log("提取到abstract-all内容:", abstractText.substring(0, 50) + '...');
            } else {
                console.log("abstract-all未找到文本内容");
            }
        } else {
            console.log("找不到abstract-all元素");
        }
        
        // 提取content-all文本内容 (尝试多种选择器)
        let contentElement = document.getElementById('content-all') || 
                          document.querySelector('#content-all') ||
                          document.querySelector('span#content-all');
        
        // 如果直接找不到content-all，尝试找包含它的div.descrip
        if (!contentElement) {
            descriptionContainers.forEach((container, index) => {
                if (container.querySelector('#content-all') || container.innerHTML.includes('content-all')) {
                    console.log(`在第${index + 1}个descrip容器中找到content-all`);
                    contentElement = container;
                }
            });
        }
        
        if (contentElement) {
            console.log("找到content-all元素:", contentElement);
            // 使用innerHTML查看原始内容进行调试
            console.log("content-all原始HTML:", contentElement.innerHTML);
            
            const paragraphs = contentElement.querySelectorAll('p');
            console.log(`content-all中找到${paragraphs.length}个段落`);
            
            let contentText = '';
            paragraphs.forEach(p => {
                if (!p.querySelector('img')) { // 跳过只包含图片的段落
                    contentText += p.textContent.trim() + '\n';
                }
            });
            
            // 如果没找到段落，尝试直接获取文本内容
            if (!contentText && contentElement.textContent) {
                contentText = contentElement.textContent.trim();
            }
            
            if (contentText) {
                descriptions.content = contentText.trim();
                console.log("提取到content-all内容:", contentText.substring(0, 50) + '...');
            } else {
                console.log("content-all未找到文本内容");
            }
        } else {
            console.log("找不到content-all元素");
        }
        
        // 如果没有找到任何内容，尝试查找任何div.descrip内容作为备选
        if (Object.keys(descriptions).length === 0 && descriptionContainers.length > 0) {
            console.log("未找到指定ID的内容，尝试从所有descrip容器中提取");
            descriptionContainers.forEach((container, index) => {
                console.log(`检查第${index + 1}个descrip容器的内容`);
                
                // 提取图片
                const images = container.querySelectorAll('img');
                if (images.length > 0) {
                    const imageUrls = [];
                    images.forEach(img => {
                        let imgSrc = img.getAttribute('src');
                        if (imgSrc) {
                            if (!imgSrc.startsWith('http')) {
                                imgSrc = 'http:' + imgSrc;
                            }
                            imageUrls.push(imgSrc);
                        }
                    });
                    if (imageUrls.length > 0 && !descriptions.feature) {
                        descriptions.feature = imageUrls;
                        console.log(`从第${index + 1}个descrip容器提取到${imageUrls.length}张图片`);
                    }
                }
                
                // 提取文本
                const paragraphs = container.querySelectorAll('p');
                let textContent = '';
                paragraphs.forEach(p => {
                    if (!p.querySelector('img')) { // 跳过只包含图片的段落
                        textContent += p.textContent.trim() + '\n';
                    }
                });
                
                // 如果没找到段落，尝试直接获取文本内容
                if (!textContent && container.textContent) {
                    textContent = container.textContent.trim();
                }
                
                if (textContent) {
                    // 根据内容特征决定放在哪个分类中
                    if (!descriptions.abstract && textContent.length > 0) {
                        descriptions.abstract = textContent.trim();
                        console.log(`从第${index + 1}个descrip容器提取文本作为abstract`);
                    } else if (!descriptions.content && textContent.length > 0) {
                        descriptions.content = textContent.trim();
                        console.log(`从第${index + 1}个descrip容器提取文本作为content`);
                    }
                }
            });
        }
        
        // 使用JSON格式输出所有描述
        if (Object.keys(descriptions).length > 0) {
            bookInfo.内容简介 = descriptions;
            console.log("成功提取到内容简介:", Object.keys(descriptions).join(', '));
        } else {
            console.log("警告: 未能提取到任何内容简介");
            // 设置一个空对象，避免undefined
            bookInfo.内容简介 = {};
        }
        
        return descriptions;
    }

    // 提取出版信息
    function extractPublishInfo() {
        // 提取出版时间 - 使用原生JS方法查找包含特定文本的元素
        const publishTimeElement = findElementContainingText('span.t1', '出版时间');
        if (publishTimeElement) {
            const timeText = publishTimeElement.textContent;
            const match = timeText.match(/出版时间:([^&]*)/);
            if (match && match[1]) {
                bookInfo.出版时间 = match[1].trim();
                console.log("提取到出版时间:", bookInfo.出版时间);
            }
        }
        
        // 提取出版社 - 使用属性选择器
        const publisherElement = document.querySelector('span.t1[dd_name="出版社"]');
        if (publisherElement) {
            const publisherLink = publisherElement.querySelector('a');
            if (publisherLink) {
                bookInfo.出版社 = publisherLink.textContent.trim();
                console.log("提取到出版社:", bookInfo.出版社);
            }
        }
        
        // 提取ISBN - 使用原生JS方法查找包含特定文本的元素
        const isbnElement = findElementContainingText('li', '国际标准书号ISBN');
        if (isbnElement) {
            const isbnText = isbnElement.textContent;
            const match = isbnText.match(/ISBN[：:]\s*(\d+)/);
            if (match && match[1]) {
                bookInfo.ISBN = match[1].trim();
                console.log("提取到ISBN:", bookInfo.ISBN);
            }
        }
    }

    // 提取封面图片
    function extractCoverImage() {
        const imgElement = document.querySelector('#largePic');
        if (imgElement) {
            let imgSrc = imgElement.getAttribute('src');
            if (imgSrc) {
                // 确保URL是完整的
                if (!imgSrc.startsWith('http')) {
                    imgSrc = 'http:' + imgSrc;
                }
                bookInfo.封面 = imgSrc;
                console.log("提取到封面图片:", bookInfo.封面);
            }
        }
    }

    // 提取评分信息
    function extractRating() {
        const ratingElement = document.querySelector('#comm_num_down');
        if (ratingElement) {
            bookInfo.评分 = ratingElement.textContent.trim();
            console.log("提取到评分:", bookInfo.评分);
        }
    }

    // 提取关联图书
    function extractRelatedBooks() {
        // 清空之前的结果
        bookInfo.关联图书 = [];
        
        // 找到div.over内的所有图书项
        const relatedBookElements = document.querySelectorAll('div.over ul.none_b li');
        
        if (relatedBookElements && relatedBookElements.length > 0) {
            console.log(`找到${relatedBookElements.length}本关联图书`);
            
            relatedBookElements.forEach((bookItem) => {
                // 从每个li找到书名和链接
                const nameElement = bookItem.querySelector('p.name a');
                
                if (nameElement) {
                    const title = nameElement.getAttribute('title') || nameElement.textContent.trim();
                    let url = nameElement.getAttribute('href') || '';
                    
                    // 确保URL是完整的
                    if (url && !url.startsWith('http')) {
                        const baseUrl = window.location.origin;
                        url = baseUrl + (url.startsWith('/') ? '' : '/') + url;
                    }
                    
                    // 只保留书名和URL
                    if (title && url && 
                        !bookInfo.关联图书.some(book => book.title === title)) {
                        bookInfo.关联图书.push({
                            title: title,
                            url: url
                        });
                        console.log(`提取到关联图书: ${title}`);
                    }
                }
            });
            
            console.log(`成功提取了${bookInfo.关联图书.length}本关联图书`);
        } else {
            console.log("未找到关联图书区域");
            
            // 尝试查找其他可能包含图书列表的区域
            const otherListAreaElements = document.querySelectorAll('div.list_page li');
            if (otherListAreaElements && otherListAreaElements.length > 0) {
                console.log(`找到备选区域中的${otherListAreaElements.length}本关联图书`);
                
                otherListAreaElements.forEach((bookItem) => {
                    const nameElement = bookItem.querySelector('p.name a');
                    
                    if (nameElement) {
                        const title = nameElement.getAttribute('title') || nameElement.textContent.trim();
                        let url = nameElement.getAttribute('href') || '';
                        
                        // 确保URL是完整的
                        if (url && !url.startsWith('http')) {
                            const baseUrl = window.location.origin;
                            url = baseUrl + (url.startsWith('/') ? '' : '/') + url;
                        }
                        
                        // 只保留书名和URL
                        if (title && url && 
                            !bookInfo.关联图书.some(book => book.title === title)) {
                            bookInfo.关联图书.push({
                                title: title,
                                url: url
                            });
                            console.log(`提取到关联图书: ${title}`);
                        }
                    }
                });
            }
        }
        
        // 添加一个固定的读者评论链接
        bookInfo.读者评论 = [{
            title: "心理学新书排行榜-近7日新书热卖榜",
            url: "http://bang.dangdang.com/books/newhotsales/01.31.00.00.00.00-recent7-0-0-1-1"
        }];
    }

    // 执行所有提取函数
    function extractAllInfo() {
        console.log("开始提取当当网图书信息...");
        extractTitle();
        extractPageUrl();
        extractAuthor();
        extractAuthorIntro();
        extractDescription();
        extractPublishInfo();
        extractCoverImage();
        extractRating();
        extractRelatedBooks();
        
        // 添加时间戳和URL信息
        bookInfo.processed_time = new Date().toISOString().replace('T', ' ').substring(0, 19);
        bookInfo.url = window.location.href;
        bookInfo.file_name = `DangDang_Book_${bookInfo.书名 || bookInfo.ISBN || 'unknown'}.html`;
        
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
            const existingLink = document.getElementById('dangdang-book-extract-download');
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
            title.style.color = '#FF6600'; // 当当网的橙色
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
            downloadLink.id = 'dangdang-book-extract-download';
            downloadLink.href = url;
            downloadLink.download = `${data.书名 || `DangDang_Book_${data.ISBN || 'unknown'}`}.json`;
            downloadLink.textContent = '点击下载JSON文件(备用)';
            downloadLink.style.display = 'block';
            downloadLink.style.padding = '8px 15px';
            downloadLink.style.backgroundColor = '#FF6600';
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
        const filename = `${data.书名 || `DangDang_Book_${data.ISBN || 'unknown'}`}.json`;
        
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
                source: 'dangdang',
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
            
            const downloadContainer = document.querySelector('#dangdang-book-extract-download').parentNode;
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