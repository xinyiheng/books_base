/**
 * Amazon Book Info Extractor - Popup Script
 * 处理浏览器插件弹出窗口的功能
 */

document.addEventListener('DOMContentLoaded', function() {
  // 获取DOM元素
  const extractBtn = document.getElementById('extractBtn');
  const settingsBtn = document.getElementById('settingsBtn');
  const statusDiv = document.getElementById('status');
  const resultsDiv = document.getElementById('results');
  const directoryPathSpan = document.getElementById('directoryPath');
  
  // 加载保存目录和本地服务状态
  loadSettings();
  
  // 添加事件监听器
  extractBtn.addEventListener('click', extractBookInfo);
  settingsBtn.addEventListener('click', openSettings);
  
  // 自动提取图书信息
  chrome.storage.local.get(['autoExtract'], function(result) {
    // 默认启用自动提取
    const autoExtract = result.autoExtract !== undefined ? result.autoExtract : true;
    
    if (autoExtract) {
      // 先检查本地服务连接状态，然后自动提取图书信息
      checkAndUpdateLocalServiceStatus(function() {
        // 自动提取图书信息
        extractBookInfo();
      });
    }
  });
  
  // 加载设置
  function loadSettings() {
    chrome.storage.local.get(['saveDirectory', 'localService'], function(result) {
      if (result.saveDirectory) {
        directoryPathSpan.textContent = result.saveDirectory;
      } else {
        directoryPathSpan.textContent = '未设置';
        showStatus('请先在设置中设置保存目录', 'warning');
        extractBtn.disabled = true;
      }
      
      // 检查本地服务状态
      checkAndUpdateLocalServiceStatus();
    });
  }
  
  // 检查并更新本地服务连接状态
  function checkAndUpdateLocalServiceStatus(callback) {
    chrome.runtime.sendMessage({action: 'getLocalServiceStatus'}, function(response) {
      console.log('获取本地服务状态:', response);
      
      if (response && response.enabled) {
        if (response.status === 'connected') {
          showStatus('本地服务已连接，可以自动处理HTML文件', 'success');
        } else if (response.status === 'disconnected') {
          showStatus('本地服务连接失败，将使用手动处理模式', 'warning');
        } else {
          // 如果状态未知，尝试重新连接
          chrome.runtime.sendMessage({
            action: 'setLocalServiceConfig',
            config: response
          }, function(updateResponse) {
            console.log('更新本地服务状态:', updateResponse);
            
            if (updateResponse && updateResponse.config && updateResponse.config.status === 'connected') {
              showStatus('本地服务已连接，可以自动处理HTML文件', 'success');
            } else {
              showStatus('本地服务连接失败，将使用手动处理模式', 'warning');
            }
            
            if (callback) callback();
          });
          return;
        }
      }
      
      if (callback) callback();
    });
  }
  
  // 检查本地服务连接状态
  function checkLocalServiceConnection() {
    chrome.runtime.sendMessage({action: 'getLocalServiceStatus'}, function(response) {
      if (response && response.status === 'connected') {
        showStatus('本地服务已连接，可以自动处理HTML文件', 'success');
      } else if (response && response.enabled && response.status === 'disconnected') {
        showStatus('本地服务连接失败，将使用手动处理模式', 'warning');
      }
    });
  }
  
  // 打开设置页面
  function openSettings() {
    chrome.tabs.create({url: 'settings.html'});
  }
  
  // 提取图书信息
  function extractBookInfo() {
    showStatus('正在提取图书信息...', 'info');
    extractBtn.disabled = true;
    
    // 获取保存目录
    chrome.storage.local.get(['saveDirectory', 'localService'], function(result) {
      if (!result.saveDirectory) {
        showStatus('请先在设置中设置保存目录', 'error');
        extractBtn.disabled = false;
        return;
      }
      
      // 获取当前标签页
      chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        const activeTab = tabs[0];
        
        // 检查是否在亚马逊图书页面
        if (!activeTab.url.includes('amazon.com') && !activeTab.url.includes('amazon.cn') && 
            !activeTab.url.includes('amazon.co.uk') && !activeTab.url.includes('amazon.co.jp')) {
          showStatus('请在亚马逊图书页面使用此插件', 'error');
          extractBtn.disabled = false;
          return;
        }
        
        if (!activeTab.url.includes('/dp/') && !activeTab.url.includes('/gp/product/')) {
          showStatus('请在亚马逊图书详情页面使用此插件', 'error');
          extractBtn.disabled = false;
          return;
        }
        
        // 从URL中提取ASIN
        const asinMatch = activeTab.url.match(/\/(?:dp|gp\/product)\/([A-Z0-9]{10})/);
        const asin = asinMatch ? asinMatch[1] : 'unknown';
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        
        console.log('正在提取图书信息，ASIN:', asin, '标签页ID:', activeTab.id);
        
        // 尝试注入内容脚本
        chrome.scripting.executeScript({
          target: { tabId: activeTab.id },
          files: ['js/content.js']
        }, function() {
          if (chrome.runtime.lastError) {
            console.error('注入内容脚本失败:', chrome.runtime.lastError.message);
            showStatus('注入内容脚本失败: ' + chrome.runtime.lastError.message, 'error');
            extractBtn.disabled = false;
            return;
          }
          
          console.log('内容脚本注入成功，发送提取消息');
          
          // 向内容脚本发送消息，提取图书信息和HTML内容
          chrome.tabs.sendMessage(
            activeTab.id, 
            {action: 'extractInfo'}, 
            function(response) {
              if (chrome.runtime.lastError) {
                console.error('提取失败:', chrome.runtime.lastError.message);
                showStatus('提取失败: ' + chrome.runtime.lastError.message, 'error');
                extractBtn.disabled = false;
                return;
              }
              
              if (!response || !response.bookInfo) {
                showStatus('无法从页面提取图书信息', 'error');
                extractBtn.disabled = false;
                return;
              }
              
              console.log('成功提取图书信息:', response.bookInfo);
              
              // 生成文件名（包含书籍标题）
              let bookTitle = response.bookInfo.title || '';
              // 清理标题，移除特殊字符，限制长度
              bookTitle = bookTitle.replace(/[\\/:*?"<>|]/g, '_').trim();
              if (bookTitle.length > 50) {
                bookTitle = bookTitle.substring(0, 50);
              }
              
              // 生成文件名（格式：ASIN_标题_时间戳）
              const fileName = bookTitle 
                ? `amazon_book_${asin}_${bookTitle}_${timestamp}`
                : `amazon_book_${asin}_${timestamp}`;
              
              // 显示提取的信息
              displayBookInfo(response.bookInfo);
              
              // 存储图书信息，以便在其他地方使用
              chrome.runtime.sendMessage({
                action: 'storeBookInfo',
                bookInfo: response.bookInfo
              });
              
              // 直接使用内存中的HTML内容，不进行下载
              showStatus('正在处理HTML...', 'info');
              
              // 向后台发送直接处理请求
              chrome.runtime.sendMessage({
                action: 'directProcessHtml',
                fileName: fileName,
                htmlContent: response.html,
                saveDirectory: result.saveDirectory,
                bookInfo: response.bookInfo
              }, function(response) {
                console.log('处理HTML响应:', response);
                
                if (response && response.success) {
                  showStatus(response.message || '处理成功！', 'success');
                } else {
                  showStatus(response && response.message ? response.message : '处理失败，请检查本地服务', 'error');
                }
                
                extractBtn.disabled = false;
              });
            }
          );
        });
      });
    });
  }
  
  // 显示图书信息
  function displayBookInfo(bookInfo) {
    document.getElementById('bookTitle').textContent = bookInfo.title || '未知';
    document.getElementById('author').textContent = bookInfo.author || '未知';
    document.getElementById('publisher').textContent = bookInfo.publisher || '未知';
    document.getElementById('pubDate').textContent = bookInfo.publicationDate || '未知';
    document.getElementById('isbn').textContent = bookInfo.isbn || '未知';
    
    // 显示封面图片
    const coverImageDiv = document.getElementById('coverImage');
    if (bookInfo.coverImage) {
      coverImageDiv.innerHTML = `<img src="${bookInfo.coverImage}" alt="封面图片">`;
    } else {
      coverImageDiv.textContent = '无封面图片';
    }
    
    // 显示描述
    const descriptionDiv = document.getElementById('description');
    if (bookInfo.description) {
      descriptionDiv.textContent = bookInfo.description;
    } else {
      descriptionDiv.textContent = '无描述';
    }
    
    // 显示作者简介
    const authorBioDiv = document.getElementById('authorBio');
    if (bookInfo.authorBio) {
      authorBioDiv.textContent = bookInfo.authorBio;
    } else {
      authorBioDiv.textContent = '无作者简介';
    }
    
    // 显示相关图书
    const relatedBooksDiv = document.getElementById('relatedBooks');
    if (bookInfo.relatedBooks && bookInfo.relatedBooks.length > 0) {
      const relatedList = bookInfo.relatedBooks.map(book => book.title).join(', ');
      relatedBooksDiv.textContent = relatedList;
    } else {
      relatedBooksDiv.textContent = '无相关图书';
    }
    
    // 显示结果区域
    resultsDiv.classList.remove('hidden');
  }
  
  // 显示状态消息
  function showStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = 'status';
    statusDiv.classList.add(type);
    statusDiv.style.display = 'block';
    
    // 如果是成功消息，3秒后自动隐藏
    if (type === 'success') {
      setTimeout(() => {
        statusDiv.style.display = 'none';
      }, 3000);
    }
  }
});
