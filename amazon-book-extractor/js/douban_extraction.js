/**
 * 豆瓣图书信息提取脚本
 */

// 监听来自popup或background的消息
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  if (request.action === 'extractInfo' && request.site === 'douban') {
    // 执行提取函数并返回结果
    const bookInfo = extractDoubanBookInfo();
    sendResponse({
      success: true,
      bookInfo: bookInfo
    });
  }
  return true; // 保持消息通道开放
});

// 提取豆瓣图书信息
function extractDoubanBookInfo() {
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
    const titleElement = document.querySelector('span[property="v:itemreviewed"]');
    if (titleElement) {
        bookInfo.书名 = titleElement.textContent.trim();
        console.log("提取到书名:", bookInfo.书名);
    }

    // 提取页面URL
    const metaUrl = document.querySelector('meta[property="og:url"]');
    if (metaUrl && metaUrl.getAttribute('content')) {
        bookInfo.书本页面 = metaUrl.getAttribute('content');
    } else {
        bookInfo.书本页面 = window.location.href;
    }
    console.log("提取到页面URL:", bookInfo.书本页面);

    // 提取作者信息
    const authorSpan = findElementContainingText('span.pl', '作者');
    if (authorSpan && authorSpan.parentNode) {
        const authorLinks = authorSpan.parentNode.querySelectorAll('a');
        if (authorLinks.length > 0) {
            bookInfo.作者 = authorLinks[0].textContent.trim();
            
            if (authorLinks.length > 1) {
                let authorUrl = authorLinks[1].getAttribute('href');
                if (authorUrl) {
                    if (authorUrl.startsWith('/')) {
                        authorUrl = 'https://book.douban.com' + authorUrl;
                    }
                    bookInfo.作者页面 = authorUrl;
                }
            } else if (authorLinks.length === 1) {
                let authorUrl = authorLinks[0].getAttribute('href');
                if (authorUrl) {
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

    // 提取作者简介
    const authorBioHeading = findElementContainingText('h2', '作者简介');
    if (authorBioHeading) {
        let element = authorBioHeading.nextElementSibling;
        while (element) {
            if (element.classList.contains('indent')) {
                const introDiv = element.querySelector('div.intro');
                if (introDiv) {
                    const paragraphs = introDiv.querySelectorAll('p');
                    if (paragraphs.length > 0) {
                        let authorBio = '';
                        paragraphs.forEach(p => {
                            authorBio += p.textContent.trim() + '\n\n';
                        });
                        bookInfo.作者简介 = authorBio.trim();
                    } else {
                        bookInfo.作者简介 = introDiv.textContent.trim();
                    }
                    break;
                } else {
                    const paragraphs = element.querySelectorAll('p');
                    if (paragraphs.length > 0) {
                        let authorBio = '';
                        paragraphs.forEach(p => {
                            authorBio += p.textContent.trim() + '\n\n';
                        });
                        bookInfo.作者简介 = authorBio.trim();
                    } else {
                        const shortSpan = element.querySelector('span.short');
                        if (shortSpan) {
                            bookInfo.作者简介 = shortSpan.textContent.trim();
                        } else {
                            bookInfo.作者简介 = element.textContent.trim();
                        }
                    }
                    break;
                }
            }
            element = element.nextElementSibling;
        }
    }

    // 提取内容简介
    const descHeading = findElementContainingText('h2', '内容简介') || 
                       findElementContainingText('span', '内容简介');
    if (descHeading) {
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
                    break;
                } else {
                    bookInfo.内容简介 = element.textContent.trim();
                    break;
                }
            }
        }
    }

    // 提取出版信息
    const infoDiv = document.getElementById('info');
    if (infoDiv) {
        // 优先提取出品方
        const producerSpans = infoDiv.querySelectorAll('span.pl');
        let publisherFound = false;
        
        // 先查找出品方
        for (let i = 0; i < producerSpans.length; i++) {
            const span = producerSpans[i];
            if (span.textContent.trim() === '出品方:') {
                const nextNode = span.nextSibling;
                if (nextNode) {
                    bookInfo.出版社 = nextNode.textContent.trim();
                    console.log("提取到出品方作为出版社:", bookInfo.出版社);
                    publisherFound = true;
                    break;
                }
            }
        }
        
        // 如果未找到出品方，尝试查找出版社
        if (!publisherFound) {
            for (let i = 0; i < producerSpans.length; i++) {
                const span = producerSpans[i];
                if (span.textContent.trim() === '出版社:') {
                    // 检查是否有链接
                    const nextA = span.nextElementSibling;
                    if (nextA && nextA.tagName === 'A') {
                        bookInfo.出版社 = nextA.textContent.trim();
                        console.log("提取到出版社(链接):", bookInfo.出版社);
                        publisherFound = true;
                        break;
                    } else {
                        // 如果没有链接，尝试获取文本节点
                        const nextNode = span.nextSibling;
                        if (nextNode) {
                            bookInfo.出版社 = nextNode.textContent.trim();
                            console.log("提取到出版社(文本):", bookInfo.出版社);
                            publisherFound = true;
                            break;
                        }
                    }
                }
            }
        }
        
        // 提取出版年份
        for (let i = 0; i < producerSpans.length; i++) {
            const span = producerSpans[i];
            if (span.textContent.trim() === '出版年:') {
                const nextNode = span.nextSibling;
                if (nextNode) {
                    bookInfo.出版时间 = nextNode.textContent.trim();
                    console.log("提取到出版年份:", bookInfo.出版时间);
                    break;
                }
            }
        }
        
        // 提取ISBN
        for (let i = 0; i < producerSpans.length; i++) {
            const span = producerSpans[i];
            if (span.textContent.trim() === 'ISBN:') {
                const nextNode = span.nextSibling;
                if (nextNode) {
                    bookInfo.ISBN = nextNode.textContent.trim();
                    console.log("提取到ISBN:", bookInfo.ISBN);
                    break;
                }
            }
        }
    }

    // 提取封面图片
    const imgElement = document.querySelector('a.nbg img') || 
                      document.querySelector('#mainpic img');
    if (imgElement) {
        let imgSrc = imgElement.getAttribute('src');
        if (imgSrc) {
            // 尝试获取更大的图片（豆瓣图片URL可以通过修改参数获取不同尺寸）
            imgSrc = imgSrc.replace(/s_ratio_poster/g, 'l_ratio_poster');
            imgSrc = imgSrc.replace(/view\/s\//g, 'view/l/');
            bookInfo.封面 = imgSrc;
            console.log("提取到封面图片:", bookInfo.封面);
        }
    }

    // 提取评分
    const ratingElement = document.querySelector('strong[property="v:average"]');
    if (ratingElement) {
        bookInfo.评分 = ratingElement.textContent.trim();
        console.log("提取到评分:", bookInfo.评分);
    }

    // 提取关联图书
    function extractRelatedBooks() {
        // 清空关联图书数组
        bookInfo.关联图书 = [];
        
        // 添加"这本书的其他版本"到关联图书
        const otherVersionsHeading = findElementContainingText('h2', '这本书的其他版本');
        if (otherVersionsHeading) {
            console.log("找到'这本书的其他版本'标题");
            
            // 提取works链接
            const worksLink = otherVersionsHeading.querySelector('a[href*="works"]');
            if (worksLink) {
                const worksUrl = worksLink.getAttribute('href');
                if (worksUrl) {
                    // 确保URL是完整的
                    const fullWorksUrl = worksUrl.startsWith('/') ? 'https://book.douban.com' + worksUrl : worksUrl;
                    
                    // 将"这本书的其他版本"作为特殊的关联图书添加
                    bookInfo.关联图书.push({
                        title: '本书的其他版本',
                        url: fullWorksUrl
                    });
                    
                    console.log(`添加了本书的其他版本链接: ${fullWorksUrl}`);
                }
            }
        }
        
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
                    // 提取评论者信息 - 从comment-info中提取
                    const commentInfo = item.querySelector('span.comment-info');
                    let commenterName = '匿名';
                    let time = '';
                    
                    if (commentInfo) {
                        // 提取用户名
                        const userLink = commentInfo.querySelector('a[href^="https://www.douban.com/people/"]');
                        if (userLink) {
                            commenterName = userLink.textContent.trim();
                        }
                        
                        // 提取评论时间
                        const timeLink = commentInfo.querySelector('a.comment-time');
                        if (timeLink) {
                            time = timeLink.textContent.trim();
                        }
                    }
                    
                    // 提取评分 - 从user-stars类提取
                    let rating = '';
                    const ratingSpan = item.querySelector('span.user-stars[class*="allstar"]');
                    if (ratingSpan) {
                        const ratingClass = ratingSpan.getAttribute('class') || '';
                        const ratingMatch = ratingClass.match(/allstar(\d+)/);
                        if (ratingMatch) {
                            const stars = parseInt(ratingMatch[1]) / 10;
                            
                            // 检查是否有title属性
                            const ratingTitle = ratingSpan.getAttribute('title');
                            if (ratingTitle) {
                                rating = `${stars}星 (${ratingTitle})`;
                            } else {
                                rating = `${stars}星`;
                            }
                        }
                    }
                    
                    // 提取评论内容 - 从comment-content中提取
                    let content = '';
                    const commentContent = item.querySelector('p.comment-content');
                    if (commentContent) {
                        const shortSpan = commentContent.querySelector('span.short');
                        if (shortSpan) {
                            content = shortSpan.textContent.trim();
                        } else {
                            content = commentContent.textContent.trim();
                        }
                    }
                    
                    // 构建评论对象
                    if (content) {
                        bookInfo.读者评论.push({
                            user: commenterName,
                            rating: rating,
                            content: content,
                            time: time
                        });
                        console.log(`提取到评论: ${commenterName}, 时间: ${time}, 评分: ${rating}`);
                    }
                }
            });
            
            console.log(`共提取到${bookInfo.读者评论.length}条评论`);
        }
    }

    // 调用提取函数
    extractRelatedBooks();
    extractComments();

    return bookInfo;
} 