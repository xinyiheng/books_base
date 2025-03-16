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

    console.log('发送请求到本地服务:', localServiceConfig.url);
    
    // 发送请求到本地服务
    fetch(`${localServiceConfig.url}/process`, {
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
      console.log('本地服务处理HTML成功:', data);
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
      console.error('通过本地服务处理HTML失败:', error);
      // 如果本地服务处理失败，回退到提示用户手动处理
      runPythonScript(fileName, saveDirectory, bookInfo, callback);
    });
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

// 初始化扩展
function initExtension() {
  console.log('初始化扩展...');
  loadLocalServiceConfig();
  
  // 定期检查本地服务连接状态（每5分钟）
  setInterval(function() {
    if (localServiceConfig.enabled) {
      checkLocalServiceConnection(function(status) {
        if (localServiceConfig.status !== status) {
          console.log('本地服务连接状态已更改:', status);
          localServiceConfig.status = status;
          saveLocalServiceConfig();
        }
      });
    }
  }, 5 * 60 * 1000);
}

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

// 在扩展启动时初始化
initExtension();
