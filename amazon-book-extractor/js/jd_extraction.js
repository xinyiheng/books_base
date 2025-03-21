/**
 * 京东图书信息提取脚本
 */

// 监听来自popup或background的消息
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  if (request.action === 'extractInfo' && request.site === 'jd') {
    // 执行提取函数并返回结果
    const bookInfo = extractJDBookInfo();
    sendResponse({
      success: true,
      bookInfo: bookInfo
    });
  }
  return true; // 保持消息通道开放
});

// 提取京东图书信息
function extractJDBookInfo() {
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
        "读者评论": []
    };

    // 提取书名
    const titleElement = document.querySelector('.sku-name');
    if (titleElement) {
        bookInfo.书名 = titleElement.innerText.trim();
        console.log("提取到书名:", bookInfo.书名);
    }

    // 提取页面URL
    const canonicalLink = document.querySelector('link[rel="canonical"]');
    if (canonicalLink) {
        const href = canonicalLink.getAttribute('href');
        bookInfo.书本页面 = href.startsWith('//') ? 'https:' + href : href;
    } else {
        bookInfo.书本页面 = window.location.href;
    }
    console.log("提取到页面URL:", bookInfo.书本页面);

    // 提取作者信息
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

    // 提取内容简介
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

    // 提取出版信息
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

    // 提取封面图片
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

    // 提取评分
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

    // 提取关联图书
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
                    !bookInfo.关联图书.some(book => book === title)) {
                    
                    bookInfo.关联图书.push(title + " - " + url);
                    console.log(`提取到关联图书${bookInfo.关联图书.length}: ${title}`);
                }
            }
        });
    } else {
        // 备用方法1：查找任何包含图书列表的容器
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
                            !bookInfo.关联图书.some(book => book === title)) {
                            
                            bookInfo.关联图书.push(title + " - " + url);
                            console.log(`备用方法提取到关联图书: ${title}`);
                        }
                    }
                });
                
                // 如果找到了足够的相关图书，就不再继续查找
                if (bookInfo.关联图书.length > 0) break;
            }
        }
    }

    return bookInfo;
} 