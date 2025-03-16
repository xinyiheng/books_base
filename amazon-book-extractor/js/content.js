/**
 * Amazon Book Info Extractor - Content Script
 * 在亚马逊图书页面上运行，提取图书信息和HTML内容
 */

// 监听来自popup的消息
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  if (request.action === 'extractInfo') {
    // 提取图书信息和HTML内容
    const bookInfo = extractBookInfo();
    const html = document.documentElement.outerHTML;
    
    sendResponse({
      bookInfo: bookInfo,
      html: html
    });
  }
  return true;
});

// 提取图书信息
function extractBookInfo() {
  try {
    // 初始化图书信息对象
    const bookInfo = {
      title: '',
      author: '',
      publisher: '',
      publicationDate: '',
      isbn: '',
      coverImage: '',
      description: '',
      authorBio: '',
      relatedBooks: []
    };
    
    // 提取标题
    const titleElement = document.getElementById('productTitle');
    if (titleElement) {
      bookInfo.title = titleElement.textContent.trim();
    }
    
    // 提取作者
    const authorElements = document.querySelectorAll('.author .contributorNameID, .author a:not(.contributorNameID)');
    if (authorElements.length > 0) {
      const authors = [];
      authorElements.forEach(element => {
        const authorName = element.textContent.trim();
        if (authorName && !authors.includes(authorName)) {
          authors.push(authorName);
        }
      });
      bookInfo.author = authors.join(', ');
    }
    
    // 提取出版商和出版日期
    const detailsElements = document.querySelectorAll('#detailBullets_feature_div li, #detailBulletsWrapper_feature_div li, .detail-bullet-list li');
    detailsElements.forEach(element => {
      const text = element.textContent.trim();
      
      if (text.includes('出版社') || text.includes('Publisher')) {
        const publisherMatch = text.match(/出版社\s*:\s*([^;]+)/) || text.match(/Publisher\s*:\s*([^;]+)/);
        if (publisherMatch && publisherMatch[1]) {
          bookInfo.publisher = publisherMatch[1].trim();
        }
      }
      
      if (text.includes('出版日期') || text.includes('Publication date')) {
        const dateMatch = text.match(/出版日期\s*:\s*([^;]+)/) || text.match(/Publication date\s*:\s*([^;]+)/);
        if (dateMatch && dateMatch[1]) {
          bookInfo.publicationDate = dateMatch[1].trim();
        }
      }
      
      if (text.includes('ISBN-10') || text.includes('ISBN-13')) {
        const isbnMatch = text.match(/ISBN-(?:10|13)\s*:\s*([0-9X-]+)/);
        if (isbnMatch && isbnMatch[1]) {
          bookInfo.isbn = isbnMatch[1].trim();
        }
      }
    });
    
    // 尝试从产品详情表格中提取信息
    const productDetailsTable = document.getElementById('productDetailsTable');
    if (productDetailsTable) {
      const rows = productDetailsTable.querySelectorAll('tr');
      rows.forEach(row => {
        const text = row.textContent.trim();
        
        if (text.includes('出版商') || text.includes('Publisher')) {
          const publisherMatch = text.match(/出版商\s*:\s*([^;]+)/) || text.match(/Publisher\s*:\s*([^;]+)/);
          if (publisherMatch && publisherMatch[1] && !bookInfo.publisher) {
            bookInfo.publisher = publisherMatch[1].trim();
          }
        }
        
        if (text.includes('出版日期') || text.includes('Publication date')) {
          const dateMatch = text.match(/出版日期\s*:\s*([^;]+)/) || text.match(/Publication date\s*:\s*([^;]+)/);
          if (dateMatch && dateMatch[1] && !bookInfo.publicationDate) {
            bookInfo.publicationDate = dateMatch[1].trim();
          }
        }
        
        if ((text.includes('ISBN-10') || text.includes('ISBN-13')) && !bookInfo.isbn) {
          const isbnMatch = text.match(/ISBN-(?:10|13)\s*:\s*([0-9X-]+)/);
          if (isbnMatch && isbnMatch[1]) {
            bookInfo.isbn = isbnMatch[1].trim();
          }
        }
      });
    }
    
    // 提取封面图片
    const imageElement = document.getElementById('imgBlkFront') || document.getElementById('ebooksImgBlkFront');
    if (imageElement) {
      bookInfo.coverImage = imageElement.getAttribute('src');
    } else {
      const altImageElement = document.getElementById('main-image') || document.querySelector('#imageBlock img');
      if (altImageElement) {
        bookInfo.coverImage = altImageElement.getAttribute('src');
      }
    }
    
    // 提取描述
    const descriptionElement = document.getElementById('bookDescription_feature_div') || document.querySelector('#productDescription .content');
    if (descriptionElement) {
      bookInfo.description = descriptionElement.textContent.trim();
    }
    
    // 提取作者简介
    const authorBioElement = document.getElementById('authorBio_feature_div');
    if (authorBioElement) {
      bookInfo.authorBio = authorBioElement.textContent.trim()
        .replace('作者简介', '')
        .replace('About the Author', '')
        .trim();
    }
    
    // 提取相关图书
    const relatedBooksElements = document.querySelectorAll('#sims-consolidated-1_feature_div .a-carousel-card, #sims-consolidated-2_feature_div .a-carousel-card');
    relatedBooksElements.forEach(element => {
      const titleElement = element.querySelector('.a-size-base');
      if (titleElement) {
        const title = titleElement.textContent.trim();
        const linkElement = element.querySelector('a');
        const link = linkElement ? linkElement.getAttribute('href') : '';
        
        if (title) {
          bookInfo.relatedBooks.push({
            title: title,
            link: link
          });
        }
      }
    });
    
    return bookInfo;
  } catch (error) {
    console.error('提取图书信息时发生错误:', error);
    return null;
  }
}
