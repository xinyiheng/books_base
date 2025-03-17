/**
 * Amazon Book Info Extractor - Background Script
 * 处理后台任务，包括与本地服务通信和处理HTML文件
 */

// 默认本地服务配置
let localServiceConfig = {
  enabled: false,
  url: 'http://localhost:5001', // 本地开发URL
  cloudUrl: '', // 云服务URL，例如：'https://amazon-book-extractor.zeabur.app'
  useCloud: false, // 是否使用云服务
  status: 'unknown' // unknown, connected, disconnected
};

// 当前图书信息缓存
let currentBookInfo = null;

// 监听来自popup或设置页面的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getLocalServiceStatus') {
    // 获取本地服务状态
    checkLocalServiceConnection((status) => {
      sendResponse({...localServiceConfig, status: status});
    });
    return true; // 保持消息通道开放，以便异步响应
  } 
  else if (request.action === 'setLocalServiceConfig') {
    // 设置本地服务配置
    localServiceConfig = request.config;
    saveLocalServiceConfig();
    checkLocalServiceConnection((status) => {
      sendResponse({success: true, config: {...localServiceConfig, status: status}});
    });
    return true; // 保持消息通道开放，以便异步响应
  }
  else if (request.action === 'createDirectories') {
    // 创建必要的目录
    if (localServiceConfig.enabled && localServiceConfig.status === 'connected') {
      // 使用本地服务创建目录
      createDirectoriesViaLocalService(request.saveDirectory, sendResponse);
    } else {
      // 使用旧方法（提示用户手动创建）
      createDirectories(request.saveDirectory, sendResponse);
    }
    return true; // 保持消息通道开放，以便异步响应
  } 
  else if (request.action === 'runPythonScript') {
    // 运行Python脚本处理HTML文件
    if (localServiceConfig.enabled && localServiceConfig.status === 'connected') {
      // 使用本地服务处理HTML
      processHtmlViaLocalService(request.fileName, request.htmlContent, request.saveDirectory, request.bookInfo, sendResponse);
    } else {
      // 使用旧方法（提示用户手动运行Python脚本）
      runPythonScript(request.fileName, request.saveDirectory, request.bookInfo, sendResponse);
    }
    return true; // 保持消息通道开放，以便异步响应
  }
  else if (request.action === 'processHtmlViaLocalService') {
    // 直接使用本地服务处理HTML
    if (localServiceConfig.enabled && localServiceConfig.status === 'connected') {
      // 使用本地服务处理HTML
      processHtmlViaLocalService(request.fileName, request.htmlContent, request.saveDirectory, request.bookInfo, sendResponse);
    } else {
      // 如果本地服务不可用，回退到旧方法
      runPythonScript(request.fileName, request.saveDirectory, request.bookInfo, sendResponse);
    }
    return true; // 保持消息通道开放，以便异步响应
  }
  else if (request.action === 'directProcessHtml') {
    // 直接处理HTML内容（不使用下载API）
    directProcessHtml(request.fileName, request.htmlContent, request.saveDirectory, request.bookInfo, sendResponse);
    return true; // 保持消息通道开放，以便异步响应
  }
  else if (request.action === 'storeBookInfo') {
    // 存储图书信息，以便popup可以使用
    currentBookInfo = request.bookInfo;
    chrome.storage.local.set({ currentBookInfo: request.bookInfo });
    sendResponse({success: true});
    return false; // 不需要异步响应
  }
  else if (request.action === 'getCurrentBookInfo') {
    // 获取当前图书信息
    if (currentBookInfo) {
      sendResponse({success: true, bookInfo: currentBookInfo});
    } else {
      chrome.storage.local.get(['currentBookInfo'], function(result) {
        if (result.currentBookInfo) {
          currentBookInfo = result.currentBookInfo;
          sendResponse({success: true, bookInfo: currentBookInfo});
        } else {
          sendResponse({success: false, message: '没有可用的图书信息'});
        }
      });
      return true; // 保持消息通道开放，以便异步响应
    }
    return false;
  }
});

// 加载本地服务配置
function loadLocalServiceConfig() {
  chrome.storage.local.get(['localService'], function(result) {
    if (result.localService) {
      localServiceConfig = result.localService;
      console.log('已加载本地服务配置:', localServiceConfig);
      
      // 如果本地服务已启用，检查连接状态
      if (localServiceConfig.enabled) {
        checkLocalServiceConnection(function(status) {
          console.log('本地服务连接状态:', status);
          localServiceConfig.status = status;
          saveLocalServiceConfig();
          
          // 如果连接成功，同步配置到本地服务
          if (status === 'connected') {
            syncConfigToLocalService();
          }
        });
      }
    }
  });
}

// 保存本地服务配置
function saveLocalServiceConfig() {
  chrome.storage.local.set({localService: localServiceConfig}, function() {
    console.log('已保存本地服务配置:', localServiceConfig);
  });
}

// 同步配置到本地服务
function syncConfigToLocalService() {
  chrome.storage.local.get(['saveDirectory', 'feishuWebhook'], function(result) {
    if (result.saveDirectory) {
      const configData = {
        save_directory: result.saveDirectory
      };
      
      if (result.feishuWebhook) {
        configData.feishu_webhook = result.feishuWebhook;
      }
      
      // 发送配置到本地服务
      fetch(`${localServiceConfig.url}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configData)
      })
      .then(response => response.json())
      .then(data => {
        console.log('配置已同步到本地服务:', data);
      })
      .catch(error => {
        console.error('同步配置到本地服务失败:', error);
      });
    }
  });
}

// 检查本地服务连接状态
function checkLocalServiceConnection(callback) {
  if (!localServiceConfig.enabled) {
    localServiceConfig.status = 'disabled';
    saveLocalServiceConfig();
    if (callback) callback('disabled');
    return;
  }

  // 确定要使用的URL
  const serviceUrl = localServiceConfig.useCloud && localServiceConfig.cloudUrl 
    ? localServiceConfig.cloudUrl 
    : localServiceConfig.url;

  fetch(`${serviceUrl}/status`, { 
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    // 添加超时设置，避免长时间等待
    signal: AbortSignal.timeout(5000)
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    localServiceConfig.status = 'connected';
    saveLocalServiceConfig();
    console.log('服务连接成功:', data);
    if (callback) callback('connected');
  })
  .catch(error => {
    localServiceConfig.status = 'disconnected';
    saveLocalServiceConfig();
    console.error('服务连接失败:', error);
    if (callback) callback('disconnected');
  });
}

// 通过本地服务创建目录
function createDirectoriesViaLocalService(saveDirectory, callback) {
  fetch(`${localServiceConfig.url}/create_directories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ saveDirectory: saveDirectory })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    if (data.success) {
      callback({ success: true, message: '目录已成功创建' });
    } else {
      callback({ success: false, message: data.message || '创建目录失败' });
    }
  })
  .catch(error => {
    console.error('通过本地服务创建目录失败:', error);
    callback({ 
      success: false, 
      message: `通过本地服务创建目录失败: ${error.message}。请确保本地服务正在运行。` 
    });
  });
}

// 通过本地服务处理HTML
function processHtmlViaLocalService(fileName, htmlContent, saveDirectory, bookInfo, callback) {
  console.log('通过本地服务处理HTML:', fileName);
  
  // 准备请求数据
  const requestData = {
    html: htmlContent,
    filename: fileName,
    saveDirectory: saveDirectory,
    bookInfo: bookInfo
  };

  // 获取飞书Webhook URL
  chrome.storage.local.get(['feishuWebhook'], function(result) {
    if (result.feishuWebhook) {
      requestData.feishuWebhook = result.feishuWebhook;
    }

    // 优先尝试使用本地服务处理HTML
    const tryProcessViaService = () => {
      let serviceUrl = localServiceConfig.url;
      // 如果配置了使用云服务且有云服务URL，则使用云服务
      if (localServiceConfig.useCloud && localServiceConfig.cloudUrl) {
        serviceUrl = localServiceConfig.cloudUrl;
        console.log('使用云服务进行处理:', serviceUrl);
      }
      
      console.log('发送请求到服务:', serviceUrl);
      
      // 设置超时防止请求挂起
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10秒超时
      
      // 发送请求到本地或云服务
      fetch(`${serviceUrl}/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData),
        signal: controller.signal
      })
      .then(response => {
        clearTimeout(timeoutId);
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        console.log('服务处理HTML成功:', data);
        if (data.success) {
          callback({ 
            success: true, 
            message: '处理成功! JSON和Markdown文件已生成' + (requestData.feishuWebhook ? '，数据已发送到飞书。' : '。'),
            files: data.files,
            bookInfo: data.book_info
          });
          
          // 连接成功后更新状态
          if (localServiceConfig.status !== 'connected') {
            localServiceConfig.status = 'connected';
            saveLocalServiceConfig();
          }
        } else {
          callback({ success: false, message: data.message || '处理失败' });
        }
      })
      .catch(error => {
        clearTimeout(timeoutId);
        console.error('通过服务处理HTML失败:', error);
        
        // 尝试直接处理文件
        handleLocalProcessing();
      });
    };
    
    // 处理本地文件（无需服务器）
    const handleLocalProcessing = () => {
      try {
        // 更新服务状态
        localServiceConfig.status = 'disconnected';
        saveLocalServiceConfig();
        
        // 直接保存HTML到本地
        const htmlBlob = new Blob([htmlContent], {type: 'text/html'});
        const htmlUrl = URL.createObjectURL(htmlBlob);
        
        // 不显示保存对话框下载HTML
        chrome.downloads.download({
          url: htmlUrl,
          filename: `${fileName}.html`,
          saveAs: false
        }, (downloadId) => {
          if (chrome.runtime.lastError) {
            console.error('保存HTML失败:', chrome.runtime.lastError);
            callback({ 
              success: false, 
              message: '保存HTML失败，请检查浏览器下载设置'
            });
            return;
          }
          
          // 创建JSON文件内容
          const jsonContent = JSON.stringify(bookInfo, null, 2);
          const jsonBlob = new Blob([jsonContent], {type: 'application/json'});
          const jsonUrl = URL.createObjectURL(jsonBlob);
          
          // 不显示保存对话框下载JSON
          chrome.downloads.download({
            url: jsonUrl,
            filename: `${fileName}.json`,
            saveAs: false
          }, () => {
            // 即使保存JSON失败也继续处理
            callback({ 
              success: true, 
              message: '已保存HTML和JSON文件，但本地服务连接失败，无法自动生成Markdown',
              files: {
                html: `${fileName}.html`,
                json: `${fileName}.json`
              }
            });
          });
        });
      } catch (error) {
        console.error('本地处理失败:', error);
        callback({ 
          success: false, 
          message: '本地处理失败: ' + error.message
        });
      }
    };
    
    // 根据配置决定处理方式
    if (localServiceConfig.enabled) {
      tryProcessViaService();
    } else {
      handleLocalProcessing();
    }
  });
}

// 运行Python脚本处理HTML文件（旧方法）
function runPythonScript(fileName, saveDirectory, bookInfo, callback) {
  // 检查本地服务是否可用
  if (localServiceConfig.enabled && localServiceConfig.status === 'connected') {
    // 如果本地服务可用，尝试使用本地服务处理
    // 由于我们没有HTML内容，所以需要构造HTML文件路径
    const htmlFilePath = `${saveDirectory}/html/${fileName}.html`;
    
    // 准备请求数据
    const requestData = {
      filename: `${fileName}.html`,
      saveDirectory: saveDirectory,
      bookInfo: bookInfo,
      htmlFilePath: htmlFilePath
    };
    
    // 获取飞书Webhook URL
    chrome.storage.local.get(['feishuWebhook'], function(result) {
      if (result.feishuWebhook) {
        requestData.feishuWebhook = result.feishuWebhook;
      }
      
      // 发送请求到本地服务
      fetch(`${localServiceConfig.url}/process_file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData)
      })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        if (data.success) {
          callback({ 
            success: true, 
            message: '处理成功! JSON和Markdown文件已生成' + (requestData.feishuWebhook ? '，数据已发送到飞书。' : '。'),
            files: data.files,
            bookInfo: data.book_info
          });
        } else {
          callback({ success: false, message: data.message || '处理失败' });
        }
      })
      .catch(error => {
        console.error('通过本地服务处理HTML文件失败:', error);
        // 如果本地服务处理失败，回退到提示用户手动处理
        fallbackToManualProcessing(fileName, saveDirectory, bookInfo, callback);
      });
    });
  } else {
    // 如果本地服务不可用，提示用户手动处理
    fallbackToManualProcessing(fileName, saveDirectory, bookInfo, callback);
  }
}

// 回退到手动处理方法
function fallbackToManualProcessing(fileName, saveDirectory, bookInfo, callback) {
  // 获取飞书Webhook URL
  chrome.storage.local.get(['feishuWebhook'], function(result) {
    const webhookUrl = result.feishuWebhook || '[YOUR_WEBHOOK_URL]';
    
    // 这里我们只是返回成功，并假设用户将手动运行Python脚本
    callback({ 
      success: true, 
      message: '请手动运行以下Python命令处理HTML文件:\n' +
        `cd ${saveDirectory} && python process_amazon_book.py --html html/${fileName}.html --output-dir ${saveDirectory} --feishu-webhook ${webhookUrl}`
    });
  });
}

// 创建必要的目录（旧方法）
function createDirectories(saveDirectory, callback) {
  // 由于浏览器扩展无法直接创建目录，我们需要提供一个提示
  // 在实际应用中，这可能需要一个本地应用程序或原生消息传递
  
  // 这里我们只是返回成功，并假设用户已经创建了必要的目录
  callback({ success: true, message: '请确保以下目录已存在:\n' +
    `${saveDirectory}/html\n` +
    `${saveDirectory}/json\n` +
    `${saveDirectory}/markdown` });
}

// 直接处理HTML内容（不使用下载API）
function directProcessHtml(fileName, htmlContent, saveDirectory, bookInfo, callback) {
  console.log('直接处理HTML内容:', fileName);
  
  // 获取本地服务配置
  chrome.storage.local.get(['localService', 'feishuWebhook'], function(result) {
    const localServiceEnabled = result.localService && result.localService.enabled;
    const feishuWebhook = result.feishuWebhook;
    
    // 准备请求数据
    const requestData = {
      html: htmlContent,
      filename: fileName,
      saveDirectory: saveDirectory,
      bookInfo: bookInfo
    };
    
    if (feishuWebhook) {
      requestData.feishuWebhook = feishuWebhook;
    }
    
    // 尝试通过本地服务处理
    const processViaService = () => {
      let serviceUrl = localServiceConfig.url;
      
      // 如果配置了使用云服务且有云服务URL，则使用云服务
      if (localServiceConfig.useCloud && localServiceConfig.cloudUrl) {
        serviceUrl = localServiceConfig.cloudUrl;
        console.log('使用云服务处理:', serviceUrl);
      }
      
      console.log('发送请求到服务:', serviceUrl);
      
      // 设置请求超时
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000); // 15秒超时
      
      fetch(`${serviceUrl}/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData),
        signal: controller.signal
      })
      .then(response => {
        clearTimeout(timeoutId);
        if (!response.ok) {
          throw new Error(`HTTP 错误! 状态: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        console.log('服务处理成功:', data);
        
        // 更新本地服务状态
        if (localServiceConfig.status !== 'connected') {
          localServiceConfig.status = 'connected';
          saveLocalServiceConfig();
        }
        
        // 发送成功响应
        callback({
          success: true,
          message: '处理成功！已生成JSON和Markdown文件' + (feishuWebhook ? '，数据已发送到飞书' : ''),
          files: data.files,
          bookInfo: data.book_info
        });
      })
      .catch(error => {
        clearTimeout(timeoutId);
        console.error('服务处理HTML失败:', error);
        
        // 更新本地服务状态
        localServiceConfig.status = 'disconnected';
        saveLocalServiceConfig();
        
        // 手动处理HTML内容
        handleManualProcessing();
      });
    };
    
    // 手动处理HTML内容（无需下载，直接写入文件）
    const handleManualProcessing = () => {
      try {
        // 保存文件到服务器失败，发送完整错误消息
        callback({
          success: false,
          message: '无法连接到本地服务，请确保本地服务正在运行。以下是几种解决方案：\n' +
                  '1. 运行local_service.py脚本启动本地服务\n' +
                  '2. 检查本地服务URL配置是否正确\n' +
                  '3. 请检查防火墙设置是否阻止了本地服务连接'
        });
      } catch (error) {
        console.error('处理失败:', error);
        callback({
          success: false,
          message: '处理失败: ' + error.message
        });
      }
    };
    
    // 根据本地服务状态决定处理方式
    if (localServiceEnabled) {
      processViaService();
    } else {
      handleManualProcessing();
    }
  });
}

// 检查通知权限
function checkNotificationPermission() {
  console.log('检查通知权限...');
  
  // 确保图标路径正确
  const iconUrl = chrome.runtime.getURL('images/icons8-books-3d-fluency-96.png');
  
  // 在Chrome扩展中，通知权限是自动授予的，但我们可以测试通知功能
  chrome.notifications.create('test-notification', {
    type: 'basic',
    iconUrl: iconUrl,
    title: 'Amazon Book Info Extractor',
    message: '扩展已加载，通知系统正常工作',
    priority: 2
  }, function(notificationId) {
    if (chrome.runtime.lastError) {
      console.error('通知创建失败:', chrome.runtime.lastError.message);
      // 尝试使用延迟重试
      setTimeout(() => {
        chrome.notifications.create('test-notification-retry', {
          type: 'basic',
          iconUrl: iconUrl,
          title: 'Amazon Book Info Extractor',
          message: '扩展已加载，通知系统正常工作',
          priority: 2
        });
      }, 1000);
    } else {
      console.log('测试通知已创建:', notificationId);
      // 3秒后自动关闭测试通知
      setTimeout(function() {
        chrome.notifications.clear(notificationId);
      }, 3000);
    }
  });
}

// 安全创建通知的辅助函数
function createSafeNotification(notificationId, options) {
  console.log('创建通知:', notificationId, options);
  
  // 确保图标路径正确
  if (!options.iconUrl || !options.iconUrl.startsWith('chrome-extension://')) {
    options.iconUrl = chrome.runtime.getURL('images/icons8-books-3d-fluency-96.png');
  }
  
  try {
    chrome.notifications.create(notificationId, options, function(createdId) {
      if (chrome.runtime.lastError) {
        console.error('通知创建失败:', chrome.runtime.lastError.message);
        // 尝试简化通知内容并重试
        const simpleOptions = {
          type: 'basic',
          iconUrl: options.iconUrl,
          title: options.title || 'Amazon Book Info Extractor',
          message: options.message || '操作完成',
          priority: 2
        };
        setTimeout(() => {
          chrome.notifications.create(notificationId + '-retry', simpleOptions);
        }, 500);
      } else {
        console.log('通知已创建:', createdId);
      }
    });
  } catch (error) {
    console.error('创建通知时发生异常:', error);
  }
}

// 安全更新通知的辅助函数
function updateSafeNotification(notificationId, options) {
  console.log('更新通知:', notificationId, options);
  
  // 确保图标路径正确
  if (!options.iconUrl || !options.iconUrl.startsWith('chrome-extension://')) {
    options.iconUrl = chrome.runtime.getURL('images/icons8-books-3d-fluency-96.png');
  }
  
  try {
    chrome.notifications.update(notificationId, options, function(wasUpdated) {
      if (chrome.runtime.lastError) {
        console.error('通知更新失败:', chrome.runtime.lastError.message);
        // 如果更新失败，尝试创建新通知
        try {
          chrome.notifications.create(notificationId + '-new', options);
        } catch (error) {
          console.error('创建替代通知时发生异常:', error);
        }
      } else {
        console.log('通知已更新:', wasUpdated);
      }
    });
  } catch (error) {
    console.error('更新通知时发生异常:', error);
    // 如果更新失败，尝试创建新通知
    try {
      chrome.notifications.create(notificationId + '-new', options);
    } catch (innerError) {
      console.error('创建替代通知时发生异常:', innerError);
    }
  }
}

// 初始化扩展
function initExtension() {
  console.log('初始化扩展...');
  
  // 加载本地服务配置
  loadLocalServiceConfig();
  
  // 检查本地服务连接状态
  checkLocalServiceConnection(function(result) {
    console.log('本地服务连接状态:', result);
  });
  
  // 添加上下文菜单
  chrome.contextMenus.create({
    id: 'extractBookInfo',
    title: '从这个页面提取图书信息',
    contexts: ['page'],
    documentUrlPatterns: ['*://*.amazon.com/*', '*://*.amazon.cn/*']
  });
  
  // 检查通知权限
  checkNotificationPermission();
}

// 直接提取图书信息（不显示popup）
function extractBookInfoDirectly(tab) {
  console.log('直接提取图书信息，标签页ID:', tab.id);
  
  // 创建一个唯一的通知ID，用于更新同一个通知
  const notificationId = 'extract-' + Date.now();
  
  // 显示开始处理的通知
  createSafeNotification(notificationId, {
    type: 'basic',
    iconUrl: 'images/icons8-books-3d-fluency-96.png',
    title: 'Amazon Book Info Extractor',
    message: '开始提取图书信息...',
    priority: 2
  });
  
  // 获取保存目录和本地服务配置
  chrome.storage.local.get(['saveDirectory', 'localService'], function(result) {
    if (!result.saveDirectory) {
      // 未设置保存目录，显示提示
      updateSafeNotification(notificationId, {
        type: 'basic',
        iconUrl: 'images/icons8-books-3d-fluency-96.png',
        title: 'Amazon Book Info Extractor - 错误',
        message: '请先在设置中设置保存目录',
        priority: 2
      });
      return;
    }
    
    // 从URL中提取ASIN
    const asinMatch = tab.url.match(/\/(?:dp|gp\/product)\/([A-Z0-9]{10})/);
    const asin = asinMatch ? asinMatch[1] : 'unknown';
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    
    // 更新通知为注入脚本阶段
    updateSafeNotification(notificationId, {
      type: 'basic',
      iconUrl: 'images/icons8-books-3d-fluency-96.png',
      title: 'Amazon Book Info Extractor',
      message: '正在注入内容脚本...',
      priority: 2
    });
    
    // 检查内容脚本是否已经注入
    chrome.tabs.sendMessage(tab.id, {action: 'ping'}, function(response) {
      const scriptAlreadyInjected = !chrome.runtime.lastError && response && response.pong;
      
      if (scriptAlreadyInjected) {
        console.log('内容脚本已注入，直接提取信息');
        extractInfoFromPage();
      } else {
        console.log('内容脚本未注入，开始注入');
        // 注入内容脚本
        chrome.scripting.executeScript({
          target: { tabId: tab.id },
          files: ['js/content.js']
        }, function() {
          if (chrome.runtime.lastError) {
            console.error('注入内容脚本失败:', chrome.runtime.lastError.message);
            
            // 显示错误提示
            updateSafeNotification(notificationId, {
              type: 'basic',
              iconUrl: 'images/icons8-books-3d-fluency-96.png',
              title: 'Amazon Book Info Extractor - 错误',
              message: '注入内容脚本失败: ' + chrome.runtime.lastError.message,
              priority: 2
            });
            return;
          }
          
          // 等待脚本初始化
          setTimeout(function() {
            extractInfoFromPage();
          }, 500); // 给内容脚本500毫秒初始化时间
        });
      }
    });
    
    // 从页面提取信息的函数
    function extractInfoFromPage() {
      // 更新通知为提取信息阶段
      updateSafeNotification(notificationId, {
        type: 'basic',
        iconUrl: 'images/icons8-books-3d-fluency-96.png',
        title: 'Amazon Book Info Extractor',
        message: '正在提取页面信息...',
        priority: 2
      });
      
      // 尝试提取信息，最多重试3次
      let retryCount = 0;
      const maxRetries = 3;
      
      function tryExtractInfo() {
        // 向内容脚本发送消息，提取图书信息和HTML内容
        chrome.tabs.sendMessage(
          tab.id, 
          {action: 'extractInfo'}, 
          function(response) {
            if (chrome.runtime.lastError) {
              console.error('提取失败:', chrome.runtime.lastError.message);
              
              if (retryCount < maxRetries) {
                retryCount++;
                console.log(`重试提取信息 (${retryCount}/${maxRetries})...`);
                
                // 更新通知为重试状态
                updateSafeNotification(notificationId, {
                  type: 'basic',
                  iconUrl: 'images/icons8-books-3d-fluency-96.png',
                  title: 'Amazon Book Info Extractor',
                  message: `提取信息失败，正在重试 (${retryCount}/${maxRetries})...`,
                  priority: 2
                });
                
                // 延迟后重试
                setTimeout(tryExtractInfo, 1000);
                return;
              }
              
              // 显示错误提示
              updateSafeNotification(notificationId, {
                type: 'basic',
                iconUrl: 'images/icons8-books-3d-fluency-96.png',
                title: 'Amazon Book Info Extractor - 错误',
                message: '提取失败: ' + chrome.runtime.lastError.message,
                priority: 2
              });
              return;
            }
            
            if (!response || !response.bookInfo) {
              // 显示错误提示
              updateSafeNotification(notificationId, {
                type: 'basic',
                iconUrl: 'images/icons8-books-3d-fluency-96.png',
                title: 'Amazon Book Info Extractor - 错误',
                message: '无法从页面提取图书信息',
                priority: 2
              });
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
            
            // 存储图书信息
            currentBookInfo = response.bookInfo;
            
            // 更新通知为处理HTML阶段
            updateSafeNotification(notificationId, {
              type: 'basic',
              iconUrl: 'images/icons8-books-3d-fluency-96.png',
              title: 'Amazon Book Info Extractor',
              message: '正在处理HTML内容...',
              priority: 2
            });
            
            // 直接处理HTML内容
            directProcessHtml(
              fileName, 
              response.html, 
              result.saveDirectory, 
              response.bookInfo, 
              function(processResult) {
                // 显示处理结果提示
                let title = processResult.success 
                  ? 'Amazon Book Info Extractor - 成功' 
                  : 'Amazon Book Info Extractor - 失败';
                  
                updateSafeNotification(notificationId, {
                  type: 'basic',
                  iconUrl: 'images/icons8-books-3d-fluency-96.png',
                  title: title,
                  message: processResult.message,
                  priority: 2
                });
                
                // 如果成功，显示文件保存位置
                if (processResult.success && processResult.files) {
                  setTimeout(function() {
                    let fileMsg = '文件已保存到:\n';
                    if (processResult.files.markdown) {
                      fileMsg += '- ' + processResult.files.markdown + '\n';
                    }
                    if (processResult.files.json) {
                      fileMsg += '- ' + processResult.files.json + '\n';
                    }
                    if (processResult.files.html) {
                      fileMsg += '- ' + processResult.files.html;
                    }
                    
                    createSafeNotification('files-' + Date.now(), {
                      type: 'basic',
                      iconUrl: 'images/icons8-books-3d-fluency-96.png',
                      title: 'Amazon Book Info Extractor - 文件位置',
                      message: fileMsg,
                      priority: 2
                    });
                  }, 2000); // 2秒后显示文件位置通知
                }
              }
            );
          }
        );
      }
      
      // 开始尝试提取信息
      tryExtractInfo();
    }
  });
}

// 监听工具栏图标点击
chrome.action.onClicked.addListener(function(tab) {
  console.log('扩展图标被点击，当前标签页URL:', tab.url);
  
  // 检查是否在亚马逊图书页面
  if (tab.url.includes('amazon.com') || tab.url.includes('amazon.cn')) {
    console.log('当前页面是亚马逊网站');
    if (tab.url.includes('/dp/') || tab.url.includes('/gp/product/')) {
      console.log('当前页面是亚马逊产品页面，开始提取信息');
      // 直接提取当前页面的信息，不显示popup
      extractBookInfoDirectly(tab);
    } else {
      console.log('不是产品页面，显示提示');
      // 不是产品页面，显示提示
      createSafeNotification('not-product-' + Date.now(), {
        type: 'basic',
        iconUrl: 'images/icons8-books-3d-fluency-96.png',
        title: 'Amazon Book Info Extractor',
        message: '请在亚马逊图书详情页面使用此插件'
      });
    }
  } else {
    console.log('不是亚马逊页面，显示提示');
    // 不是亚马逊页面，显示提示
    createSafeNotification('not-amazon-' + Date.now(), {
      type: 'basic',
      iconUrl: 'images/icons8-books-3d-fluency-96.png',
      title: 'Amazon Book Info Extractor',
      message: '请在亚马逊图书页面使用此插件'
    });
  }
});

// 安装或更新扩展时的处理
chrome.runtime.onInstalled.addListener((details) => {
  // 加载本地服务配置
  loadLocalServiceConfig();
  
  // 启动定期检查
  // scheduleLocalServiceCheck();
  
  if (details.reason === 'install') {
    // 首次安装
    chrome.tabs.create({url: 'settings.html'});
  } else if (details.reason === 'update') {
    // 更新扩展
    console.log('扩展已更新到版本:', chrome.runtime.getManifest().version);
  }
});

initExtension();
