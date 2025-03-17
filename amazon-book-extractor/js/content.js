/**
 * Amazon Book Info Extractor - Content Script
 * 在亚马逊图书页面上运行，提取图书信息和HTML内容
 */

// 监听来自popup.js的消息
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  console.log('内容脚本收到消息:', request);
  
  // 响应ping消息，用于检测脚本是否已注入
  if (request.action === 'ping') {
    console.log('收到ping消息，回复pong');
    sendResponse({pong: true});
    return true; // 保持消息通道开放
  }
  
  if (request.action === 'extractInfo') {
    console.log('开始提取图书信息...');
    
    try {
      // 提取页面HTML
      const html = document.documentElement.outerHTML;
      
      // 提取图书信息
      const bookInfo = extractBookInfo();
      
      console.log('提取的图书信息:', bookInfo);
      
      // 发送提取的信息回background.js
      sendResponse({
        success: true,
        bookInfo: bookInfo,
        html: html
      });
    } catch (error) {
      console.error('提取信息时发生错误:', error);
      sendResponse({
        success: false,
        error: error.message
      });
    }
    
    return true; // 保持消息通道开放
  }
});

// 提取图书信息的函数
function extractBookInfo() {
  // 初始化图书信息对象
  const bookInfo = {
    title: '',
    authors: [],
    publisher: '',
    publicationDate: '',
    isbn: '',
    asin: '',
    language: '',
    pages: '',
    description: '',
    price: '',
    categories: [],
    rating: '',
    ratingCount: '',
    imageUrl: '',
    url: window.location.href
  };
  
  try {
    // 提取标题
    const titleElement = document.querySelector('#productTitle');
    if (titleElement) {
      bookInfo.title = titleElement.textContent.trim();
    }
    
    // 提取作者
    const authorElements = document.querySelectorAll('.author a, .contributorNameID');
    if (authorElements.length > 0) {
      authorElements.forEach(element => {
        const author = element.textContent.trim();
        if (author && !bookInfo.authors.includes(author)) {
          bookInfo.authors.push(author);
        }
      });
    }
    
    // 提取出版信息
    const detailBullets = document.querySelectorAll('#detailBullets_feature_div li, .detail-bullet-list li');
    detailBullets.forEach(bullet => {
      const text = bullet.textContent.trim();
      
      // 出版社和出版日期
      if (text.includes('出版社') || text.includes('Publisher')) {
        const match = text.match(/:(.*?)(?:\(|$)/);
        if (match) {
          bookInfo.publisher = match[1].trim();
          
          // 提取出版日期
          const dateMatch = text.match(/\((.*?)\)/);
          if (dateMatch) {
            bookInfo.publicationDate = dateMatch[1].trim();
          }
        }
      }
      
      // 语言
      if (text.includes('语言') || text.includes('Language')) {
        const match = text.match(/:(.*?)$/);
        if (match) {
          bookInfo.language = match[1].trim();
        }
      }
      
      // 页数
      if (text.includes('页数') || text.includes('Print length') || text.includes('pages')) {
        const match = text.match(/:\s*(\d+)/);
        if (match) {
          bookInfo.pages = match[1].trim();
        }
      }
      
      // ISBN
      if (text.includes('ISBN-10') || text.includes('ISBN-13')) {
        const match = text.match(/:\s*(\d[\d\-]+)/);
        if (match) {
          bookInfo.isbn = match[1].trim();
        }
      }
      
      // ASIN
      if (text.includes('ASIN')) {
        const match = text.match(/:\s*([A-Z0-9]+)/);
        if (match) {
          bookInfo.asin = match[1].trim();
        }
      }
    });
    
    // 尝试从URL中提取ASIN（如果上面没有提取到）
    if (!bookInfo.asin) {
      const asinMatch = window.location.href.match(/\/(?:dp|gp\/product)\/([A-Z0-9]{10})/);
      if (asinMatch) {
        bookInfo.asin = asinMatch[1];
      }
    }
    
    // 提取描述
    const descriptionElement = document.querySelector('#bookDescription_feature_div .a-expander-content');
    if (descriptionElement) {
      bookInfo.description = descriptionElement.innerHTML.trim();
    }
    
    // 提取价格
    const priceElement = document.querySelector('.a-price .a-offscreen');
    if (priceElement) {
      bookInfo.price = priceElement.textContent.trim();
    }
    
    // 提取分类
    const breadcrumbs = document.querySelectorAll('#wayfinding-breadcrumbs_feature_div li a');
    if (breadcrumbs.length > 0) {
      breadcrumbs.forEach(element => {
        const category = element.textContent.trim();
        if (category && !bookInfo.categories.includes(category)) {
          bookInfo.categories.push(category);
        }
      });
    }
    
    // 提取评分
    const ratingElement = document.querySelector('#acrPopover');
    if (ratingElement) {
      const ratingText = ratingElement.getAttribute('title');
      const ratingMatch = ratingText ? ratingText.match(/([\d\.]+)/) : null;
      if (ratingMatch) {
        bookInfo.rating = ratingMatch[1];
      }
    }
    
    // 提取评分数量
    const ratingCountElement = document.querySelector('#acrCustomerReviewText');
    if (ratingCountElement) {
      const countText = ratingCountElement.textContent.trim();
      const countMatch = countText.match(/(\d[\d,]*)/);
      if (countMatch) {
        bookInfo.ratingCount = countMatch[1];
      }
    }
    
    // 提取图书封面图片URL
    const imageElement = document.querySelector('#imgBlkFront, #ebooksImgBlkFront, #main-image, #landingImage');
    if (imageElement) {
      bookInfo.imageUrl = imageElement.getAttribute('src') || imageElement.getAttribute('data-a-dynamic-image');
      
      // 如果是data-a-dynamic-image属性，需要解析JSON
      if (bookInfo.imageUrl && bookInfo.imageUrl.startsWith('{')) {
        try {
          const imageJson = JSON.parse(bookInfo.imageUrl);
          const imageUrls = Object.keys(imageJson);
          if (imageUrls.length > 0) {
            // 选择最大的图片
            let maxWidth = 0;
            let bestUrl = '';
            
            for (const url of imageUrls) {
              const dimensions = imageJson[url];
              if (dimensions[0] > maxWidth) {
                maxWidth = dimensions[0];
                bestUrl = url;
              }
            }
            
            bookInfo.imageUrl = bestUrl || imageUrls[0];
          }
        } catch (e) {
          console.error('解析图片URL时出错:', e);
        }
      }
    }
  } catch (error) {
    console.error('提取图书信息时发生错误:', error);
  }
  
  return bookInfo;
}

// 页面加载完成后通知background.js
document.addEventListener('DOMContentLoaded', function() {
  console.log('内容脚本已加载，页面准备就绪');
});

// 初始化消息
console.log('Amazon Book Info Extractor 内容脚本已注入');
