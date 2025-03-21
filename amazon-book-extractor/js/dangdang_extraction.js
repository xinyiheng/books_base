/**
 * 当当网图书信息提取脚本
 */

// 监听来自popup或background的消息
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  console.log("当当提取脚本收到消息:", request);
  
  // 响应ping消息，用于检测脚本是否已注入
  if (request.action === 'ping') {
    console.log('收到ping消息，回复pong');
    sendResponse({pong: true});
    return true; // 保持消息通道开放
  }
  
  if (request.action === 'extractInfo' && request.site === 'dangdang') {
    try {
      // 执行提取函数并返回结果
      console.log("开始提取当当图书信息");
      const bookInfo = extractDangdangBookInfo();
      console.log("提取当当图书信息完成:", bookInfo);
      sendResponse({
        success: true,
        bookInfo: bookInfo
      });
    } catch (error) {
      console.error("提取当当图书信息出错:", error);
      sendResponse({
        success: false,
        error: error.message || "提取失败"
      });
    }
  }
  return true; // 保持消息通道开放
});

// 提取当当图书信息
function extractDangdangBookInfo() {
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
        "作者简介": ""
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
    const titleElement = document.querySelector('h1[title]');
    if (titleElement) {
        bookInfo.书名 = titleElement.getAttribute('title') || titleElement.innerText.trim();
        console.log("提取到书名:", bookInfo.书名);
    }

    // 提取页面URL
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

    // 提取作者信息
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
    const publishSpan = document.querySelector('#product_info .t1');
    if (publishSpan) {
        // 查找与之相邻的内容
        const detailBox = publishSpan.parentNode;
        if (detailBox) {
            const pubInfoText = detailBox.textContent;
            
            // 提取出版社 - 修改正则表达式以更精确地匹配
            const publisherMatch = pubInfoText.match(/出版社[：:]\s*([^出版时间]+)/);
            if (publisherMatch && publisherMatch[1]) {
                bookInfo.出版社 = publisherMatch[1].trim();
                console.log("提取到出版社:", bookInfo.出版社);
            }
            
            // 提取出版时间 - 直接从整个文本中提取
            const publishTimeMatch = pubInfoText.match(/出版时间[：:]\s*([^\s]+)/);
            if (publishTimeMatch && publishTimeMatch[1]) {
                bookInfo.出版时间 = publishTimeMatch[1].trim();
                console.log("提取到出版时间:", bookInfo.出版时间);
            } else {
                // 备用方法 - 使用原生JS方法查找包含特定文本的元素
                const publishTimeElement = findElementContainingText('span.t1', '出版时间');
                if (publishTimeElement) {
                    const timeText = publishTimeElement.textContent;
                    const match = timeText.match(/出版时间[：:]([^&]*)/);
                    if (match && match[1]) {
                        bookInfo.出版时间 = match[1].trim();
                        console.log("提取到出版时间(备用方法):", bookInfo.出版时间);
                    }
                }
            }
            
            // 提取ISBN
            const isbnMatch = pubInfoText.match(/ISBN[：:]\s*([^/]+)/);
            if (isbnMatch && isbnMatch[1]) {
                bookInfo.ISBN = isbnMatch[1].trim();
                console.log("提取到ISBN:", bookInfo.ISBN);
            }
        }
    }

    // 提取封面图片
    const imgElement = document.querySelector('#main-img-slider img') || 
                      document.querySelector('.pic img') ||
                      document.querySelector('.img_box img');
    if (imgElement) {
        let imgSrc = imgElement.getAttribute('src');
        if (imgSrc) {
            if (!imgSrc.startsWith('http')) {
                imgSrc = 'http:' + imgSrc;
            }
            bookInfo.封面 = imgSrc;
            console.log("提取到封面图片:", bookInfo.封面);
        }
    }

    // 提取评分 - 改为提取评论数
    const commentNumberElement = document.querySelector('#comm_num_down');
    if (commentNumberElement) {
        // 从a标签中提取评论数
        const commentCount = commentNumberElement.textContent.trim();
        bookInfo.评分 = commentCount;
        console.log("提取到评论数:", bookInfo.评分);
    } else {
        // 备用方法
        const oldRatingElement = document.querySelector('.star > .tuijian');
        if (oldRatingElement) {
            bookInfo.评分 = oldRatingElement.textContent.trim();
            console.log("提取到评分(备用方法):", bookInfo.评分);
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
        // 添加一个固定的读者评论链接，使用正确的Markdown格式
        bookInfo.读者评论 = [{
            title: "[心理学新书排行榜-近7日新书热卖榜](http://bang.dangdang.com/books/newhotsales/01.31.00.00.00.00-recent7-0-0-1-1)",
            url: "http://bang.dangdang.com/books/newhotsales/01.31.00.00.00.00-recent7-0-0-1-1",
        }];
    }

    // 添加Markdown格式辅助函数
    function formatItemLabel(label) {
        let result = '';
        for (let i = 0; i < label.length; i += 2) {
            // 每次取2个字符
            const chars = label.substr(i, Math.min(2, label.length - i));
            result += chars + '\n';
        }
        return result.trim(); // 去除末尾的换行符
    }

    try {
        // 调用提取函数
        extractDescription();
        extractRelatedBooks();
    } catch (error) {
        console.error("调用提取函数时出错:", error);
        // 继续执行，确保返回已提取的任何数据
    }

    return bookInfo;
} 