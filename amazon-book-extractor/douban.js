/**
 * 豆瓣图书信息提取脚本
 * 专门从豆瓣网页提取图书信息
 */
(function() {
    // 创建用于存储提取信息的对象
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
        "domain": "douban.com",
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
        const titleElement = document.querySelector('span[property="v:itemreviewed"]');
        if (titleElement) {
            bookInfo.书名 = titleElement.textContent.trim();
            console.log("提取到书名:", bookInfo.书名);
        }
    }

    // 提取页面URL
    function extractPageUrl() {
        const metaUrl = document.querySelector('meta[property="og:url"]');
        if (metaUrl && metaUrl.getAttribute('content')) {
            bookInfo.书本页面 = metaUrl.getAttribute('content');
        } else {
            bookInfo.书本页面 = window.location.href;
        }
        console.log("提取到页面URL:", bookInfo.书本页面);
    }

    // 提取作者信息
    function extractAuthor() {
        // 找到包含"作者"文本的span元素
        const authorSpan = findElementContainingText('span.pl', '作者');
        
        if (authorSpan && authorSpan.parentNode) {
            // 获取作者名称和链接
            const authorLinks = authorSpan.parentNode.querySelectorAll('a');
            if (authorLinks.length > 0) {
                // 获取第一个作者名称
                bookInfo.作者 = authorLinks[0].textContent.trim();
                
                // 获取作者页面URL（第二个链接通常是作者个人页面）
                if (authorLinks.length > 1) {
                    let authorUrl = authorLinks[1].getAttribute('href');
                    if (authorUrl) {
                        // 确保URL是完整的
                        if (authorUrl.startsWith('/')) {
                            authorUrl = 'https://book.douban.com' + authorUrl;
                        }
                        bookInfo.作者页面 = authorUrl;
                    }
                } else if (authorLinks.length === 1) {
                    let authorUrl = authorLinks[0].getAttribute('href');
                    if (authorUrl) {
                        // 确保URL是完整的
                        if (authorUrl.startsWith('/')) {
                            authorUrl = 'https://book.douban.com' + authorUrl;
                        }
                        bookInfo.作者页面 = authorUrl;
                    }
                }
                
                console.log("提取到作者:", bookInfo.作者);
                console.log("提取到作者页面:", bookInfo.作者页面);
            }
        }
    }

    // 提取作者简介
    function extractAuthorBio() {
        // 找到作者简介的标题
        const authorBioHeading = findElementContainingText('h2', '作者简介');
        if (authorBioHeading) {
            console.log("找到作者简介标题元素");
            
            // 寻找紧跟着的indent和intro div
            let element = authorBioHeading.nextElementSibling;
            while (element) {
                if (element.classList.contains('indent')) {
                    console.log("找到indent元素");
                    
                    // 先尝试找intro div
                    const introDiv = element.querySelector('div.intro');
                    if (introDiv) {
                        console.log("找到intro元素");
                        const paragraphs = introDiv.querySelectorAll('p');
                        if (paragraphs.length > 0) {
                            let authorBio = '';
                            paragraphs.forEach(p => {
                                authorBio += p.textContent.trim() + '\n\n';
                            });
                            bookInfo.作者简介 = authorBio.trim();
                            console.log("从p标签提取到作者简介");
                        } else {
                            // 如果没有找到p标签，尝试直接获取文本
                            bookInfo.作者简介 = introDiv.textContent.trim();
                            console.log("从intro直接提取到作者简介文本");
                        }
                        break;
                    } else {
                        // 如果没有找到intro div，尝试从indent直接提取
                        const paragraphs = element.querySelectorAll('p');
                        if (paragraphs.length > 0) {
                            let authorBio = '';
                            paragraphs.forEach(p => {
                                authorBio += p.textContent.trim() + '\n\n';
                            });
                            bookInfo.作者简介 = authorBio.trim();
                            console.log("从indent的p标签提取到作者简介");
                        } else {
                            // 如果没有找到p标签，尝试直接获取文本
                            // 排除短内容span
                            const shortSpan = element.querySelector('span.short');
                            if (shortSpan) {
                                bookInfo.作者简介 = shortSpan.textContent.trim();
                                console.log("从short span提取到作者简介");
                            } else {
                                bookInfo.作者简介 = element.textContent.trim();
                                console.log("从indent直接提取到作者简介文本");
                            }
                        }
                        break;
                    }
                }
                element = element.nextElementSibling;
            }
            
            // 打印提取结果
            if (bookInfo.作者简介) {
                console.log("成功提取作者简介，长度:", bookInfo.作者简介.length);
            } else {
                console.log("未能提取到作者简介");
            }
        }
    }

    // 提取内容简介
    function extractDescription() {
        // 找到内容简介的标题
        const descHeading = findElementContainingText('h2', '内容简介') || 
                           findElementContainingText('span', '内容简介');
        if (descHeading) {
            // 寻找紧跟着的intro div
            let element = descHeading;
            while (element) {
                element = element.nextElementSibling;
                if (element && (element.classList.contains('intro') || element.classList.contains('indent'))) {
                    const paragraphs = element.querySelectorAll('p');
                    if (paragraphs.length > 0) {
                        let description = '';
                        paragraphs.forEach(p => {
                            description += p.textContent.trim() + '\n\n';
                        });
                        bookInfo.内容简介 = description.trim();
                        console.log("提取到内容简介");
                        break;
                    } else {
                        // 如果没有找到p标签，尝试直接获取文本
                        bookInfo.内容简介 = element.textContent.trim();
                        console.log("提取到内容简介（无段落标签）");
                        break;
                    }
                }
            }
        }
    }

    // 提取出版信息
    function extractPublishInfo() {
        // 提取出版社
        const publisherSpan = findElementContainingText('span.pl', '出版社');
        if (publisherSpan) {
            const publisherText = publisherSpan.nextSibling;
            if (publisherText) {
                bookInfo.出版社 = publisherText.textContent.replace(':', '').trim();
                console.log("提取到出版社:", bookInfo.出版社);
            }
        }
        
        // 提取出品方 - 如果出版社为空，则使用出品方信息
        if (!bookInfo.出版社 || bookInfo.出版社 === "") {
            const producerSpan = findElementContainingText('span.pl', '出品方');
            if (producerSpan) {
                const producerText = producerSpan.nextSibling;
                if (producerText) {
                    bookInfo.出版社 = producerText.textContent.replace(':', '').trim();
                    console.log("提取到出品方作为出版社:", bookInfo.出版社);
                }
            }
        }
        
        // 提取出版年份
        const pubYearSpan = findElementContainingText('span.pl', '出版年');
        if (pubYearSpan) {
            const pubYearText = pubYearSpan.nextSibling;
            if (pubYearText) {
                bookInfo.出版时间 = pubYearText.textContent.replace(':', '').trim();
                console.log("提取到出版时间:", bookInfo.出版时间);
            }
        }
        
        // 提取ISBN
        const isbnSpan = findElementContainingText('span.pl', 'ISBN');
        if (isbnSpan) {
            const isbnText = isbnSpan.nextSibling;
            if (isbnText) {
                bookInfo.ISBN = isbnText.textContent.replace(':', '').trim();
                console.log("提取到ISBN:", bookInfo.ISBN);
            }
        }
    }

    // 提取封面图片
    function extractCoverImage() {
        // 尝试从mainpic元素获取大图URL
        const coverLinkElement = document.querySelector('#mainpic a.nbg');
        if (coverLinkElement) {
            const coverUrl = coverLinkElement.getAttribute('href');
            if (coverUrl) {
                bookInfo.封面 = coverUrl;
                console.log("提取到封面图片URL:", bookInfo.封面);
                return;
            }
        }
        
        // 备用方法：直接获取图片元素
        const coverImgElement = document.querySelector('#mainpic img[rel="v:photo"]');
        if (coverImgElement) {
            // 尝试获取原图URL
            let imgSrc = coverImgElement.getAttribute('src');
            if (imgSrc) {
                // 将小图URL转换为大图URL
                if (imgSrc.includes('/s/public/')) {
                    imgSrc = imgSrc.replace('/s/public/', '/l/public/');
                }
                bookInfo.封面 = imgSrc;
                console.log("提取到封面图片URL (从img元素):", bookInfo.封面);
            }
        }
    }

    // 提取评分信息
    function extractRating() {
        // 提取评分数值
        const ratingElement = document.querySelector('strong[property="v:average"]');
        const votesElement = document.querySelector('span[property="v:votes"]');
        
        if (ratingElement && votesElement) {
            const rating = ratingElement.textContent.trim();
            const votes = votesElement.textContent.trim();
            bookInfo.评分 = `${rating} (${votes}人评价)`;
            console.log("提取到评分:", bookInfo.评分);
        } else if (ratingElement) {
            bookInfo.评分 = ratingElement.textContent.trim();
            console.log("提取到评分(无评价人数):", bookInfo.评分);
        }
    }

    // 提取关联图书
    function extractRelatedBooks() {
        // 清空关联图书数组
        bookInfo.关联图书 = [];
        
        // 方法1: 从div.content.clearfix获取关联图书
        const relatedSection = document.querySelector('div.content.clearfix');
        if (relatedSection) {
            console.log("找到div.content.clearfix区域");
            
            // 找到所有图书链接
            const bookLinks = relatedSection.querySelectorAll('a');
            
            bookLinks.forEach((link) => {
                const title = link.getAttribute('title') || link.textContent.trim();
                let url = link.getAttribute('href');
                
                // 检查是否为真正的图书链接
                if (title && url && url.includes('/subject/')) {
                    // 确保URL是完整的
                    if (url.startsWith('/')) {
                        url = 'https://book.douban.com' + url;
                    }
                    
                    // 避免重复
                    if (!bookInfo.关联图书.some(book => book.title === title)) {
                        bookInfo.关联图书.push({
                            title: title,
                            url: url
                        });
                        console.log(`提取到关联图书(方法1): ${title}`);
                    }
                }
            });
        }
        
        // 方法2: 从dd元素获取关联图书
        const ddElements = document.querySelectorAll('dd');
        if (ddElements.length > 0) {
            console.log(`找到${ddElements.length}个dd元素`);
            
            ddElements.forEach((dd) => {
                const links = dd.querySelectorAll('a');
                links.forEach((link) => {
                    const title = link.getAttribute('title') || link.textContent.trim();
                    let url = link.getAttribute('href');
                    
                    // 检查是否为真正的图书链接
                    if (title && url && url.includes('/subject/')) {
                        // 确保URL是完整的
                        if (url.startsWith('/')) {
                            url = 'https://book.douban.com' + url;
                        }
                        
                        // 避免重复
                        if (!bookInfo.关联图书.some(book => book.title === title)) {
                            bookInfo.关联图书.push({
                                title: title,
                                url: url
                            });
                            console.log(`提取到关联图书(方法2): ${title}`);
                        }
                    }
                });
            });
        }
        
        // 方法3: 查找包含"喜欢这本书的人也喜欢"的区域
        const recommendSection = document.querySelector('.block-5');
        if (recommendSection) {
            console.log("找到推荐区域block-5");
            
            const links = recommendSection.querySelectorAll('a');
            links.forEach((link) => {
                const title = link.getAttribute('title') || link.textContent.trim();
                let url = link.getAttribute('href');
                
                // 检查是否为真正的图书链接
                if (title && url && url.includes('/subject/')) {
                    // 确保URL是完整的
                    if (url.startsWith('/')) {
                        url = 'https://book.douban.com' + url;
                    }
                    
                    // 避免重复
                    if (!bookInfo.关联图书.some(book => book.title === title)) {
                        bookInfo.关联图书.push({
                            title: title,
                            url: url
                        });
                        console.log(`提取到关联图书(方法3): ${title}`);
                    }
                }
            });
        }
        
        console.log(`共提取到${bookInfo.关联图书.length}本关联图书`);
    }

    // 提取读者评论
    function extractComments() {
        // 找到评论列表
        const commentItems = document.querySelectorAll('.comment-item');
        
        if (commentItems.length > 0) {
            commentItems.forEach((item, index) => {
                // 最多提取10条评论
                if (index < 10) {
                    // 提取评论者信息
                    const commenter = item.querySelector('a.comment-info') || item.querySelector('a');
                    const commenterName = commenter ? commenter.textContent.trim() : '匿名';
                    
                    // 提取评分
                    let rating = '';
                    const ratingSpan = item.querySelector('span[class^="allstar"]');
                    if (ratingSpan) {
                        const ratingClass = ratingSpan.getAttribute('class') || '';
                        const ratingMatch = ratingClass.match(/allstar(\d+)/);
                        if (ratingMatch) {
                            const stars = parseInt(ratingMatch[1]) / 10;
                            rating = `${stars}星`;
                        }
                    }
                    
                    // 提取评论内容
                    const commentText = item.querySelector('.comment-content') || item.querySelector('p');
                    const content = commentText ? commentText.textContent.trim() : '';
                    
                    // 提取评论时间
                    const commentTime = item.querySelector('.comment-time');
                    const time = commentTime ? commentTime.textContent.trim() : '';
                    
                    // 构建评论对象
                    if (content) {
                        bookInfo.读者评论.push({
                            user: commenterName,
                            rating: rating,
                            content: content,
                            time: time
                        });
                        console.log(`提取到评论: ${commenterName}`);
                    }
                }
            });
            
            console.log(`共提取到${bookInfo.读者评论.length}条评论`);
        }
    }

    // 执行所有提取函数
    function extractAllInfo() {
        console.log("开始提取豆瓣图书信息...");
        extractTitle();
        extractPageUrl();
        extractAuthor();
        extractAuthorBio();
        extractDescription();
        extractPublishInfo();
        extractCoverImage();
        extractRating();
        extractRelatedBooks();
        extractComments();
        
        // 添加时间戳和URL信息
        bookInfo.processed_time = new Date().toISOString().replace('T', ' ').substring(0, 19);
        bookInfo.url = window.location.href;
        bookInfo.file_name = `Douban_Book_${bookInfo.书名 || bookInfo.ISBN || 'unknown'}.html`;
        
        // 输出结果
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
            const existingLink = document.getElementById('douban-book-extract-download');
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
            title.style.color = '#2AB573'; // 豆瓣绿色
            downloadContainer.appendChild(title);
            
            // 显示提取结果数量
            const statsInfo = document.createElement('div');
            statsInfo.textContent = `找到${data.关联图书.length}本关联图书，${data.读者评论.length}条评论`;
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
            downloadLink.id = 'douban-book-extract-download';
            downloadLink.href = url;
            downloadLink.download = `${data.书名 || `Douban_Book_${data.ISBN || 'unknown'}`}.json`;
            downloadLink.textContent = '点击下载JSON文件(备用)';
            downloadLink.style.display = 'block';
            downloadLink.style.padding = '8px 15px';
            downloadLink.style.backgroundColor = '#2AB573';
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
        
        // 准备要发送的数据
        const jsonData = JSON.stringify(data, null, 2);
        const filename = `${data.书名 || `Douban_Book_${data.ISBN || 'unknown'}`}.json`;
        
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
                source: 'douban',
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
            
            const downloadContainer = document.querySelector('#douban-book-extract-download').parentNode;
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