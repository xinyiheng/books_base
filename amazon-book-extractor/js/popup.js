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
        if (!activeTab.url.includes('amazon.com') && !activeTab.url.includes('amazon.cn')) {
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
              
              // 检查本地服务是否可用
              if (result.localService && result.localService.enabled && result.localService.status === 'connected') {
                // 直接处理HTML内容，不下载
                showStatus('本地服务已连接，正在处理HTML...', 'info');
                processHtml(fileName, response.html, result.saveDirectory, response.bookInfo);
              } else {
                // 如果本地服务不可用，则下载HTML文件
                showStatus('本地服务未连接，正在下载HTML文件...', 'warning');
                downloadHtml(response.html, fileName, result.saveDirectory, response.bookInfo);
              }
            }
          );
        });
      });
    });
  }
  
  // 下载HTML内容
  function downloadHtml(html, fileName, saveDirectory, bookInfo) {
    // 创建Blob对象
    const blob = new Blob([html], {type: 'text/html'});
    const url = URL.createObjectURL(blob);
    
    // 下载HTML文件
    chrome.downloads.download({
      url: url,
      filename: `${fileName}.html`,
      saveAs: false
    }, function(downloadId) {
      if (chrome.runtime.lastError) {
        showStatus('下载HTML失败: ' + chrome.runtime.lastError.message, 'error');
        extractBtn.disabled = false;
        return;
      }
      
      showStatus('HTML已下载，请手动处理或配置本地服务', 'success');
      extractBtn.disabled = false;
      
      // 不再自动调用processHtml，而是提示用户手动处理
      // 或者配置本地服务
      const setupServiceDiv = document.createElement('div');
      setupServiceDiv.className = 'setup-service';
      setupServiceDiv.innerHTML = `
        <p>要自动处理HTML文件，请配置本地服务：</p>
        <button id="setupServiceBtn" class="btn btn-primary">配置本地服务</button>
      `;
      
      resultsDiv.appendChild(setupServiceDiv);
      
      document.getElementById('setupServiceBtn').addEventListener('click', function() {
        openSettings();
      });
    });
  }
  
  // 处理HTML文件
  function processHtml(fileName, htmlContent, saveDirectory, bookInfo) {
    console.log('正在处理HTML文件:', fileName);
    
    // 发送消息到后台脚本，处理HTML文件
    chrome.runtime.sendMessage({
      action: 'processHtmlViaLocalService',
      fileName: fileName + '.html',  // 确保文件名包含.html扩展名
      saveDirectory: saveDirectory,
      htmlContent: htmlContent,
      bookInfo: bookInfo
    }, function(response) {
      if (chrome.runtime.lastError) {
        showStatus('处理HTML失败: ' + chrome.runtime.lastError.message, 'error');
        extractBtn.disabled = false;
        return;
      }
      
      if (response && response.success) {
        showStatus(response.message, 'success');
        
        // 如果有生成的文件，显示链接
        if (response.files) {
          const filesDiv = document.createElement('div');
          filesDiv.className = 'files-list';
          
          for (const [type, path] of Object.entries(response.files)) {
            const link = document.createElement('a');
            link.href = '#';
            link.textContent = `查看${type === 'html' ? 'HTML' : type === 'json' ? 'JSON' : 'Markdown'}文件`;
            link.addEventListener('click', function() {
              chrome.tabs.create({url: `file://${path}`});
            });
            
            const fileItem = document.createElement('div');
            fileItem.appendChild(link);
            filesDiv.appendChild(fileItem);
          }
          
          bookInfoDiv.appendChild(filesDiv);
        }
      } else {
        showStatus(response ? response.message : '处理失败，未知错误', 'error');
      }
      
      extractBtn.disabled = false;
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
