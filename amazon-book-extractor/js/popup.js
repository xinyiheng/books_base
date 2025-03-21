/**
 * Amazon Book Info Extractor - Popup Script
 * 处理浏览器插件弹出窗口的功能
 */

document.addEventListener('DOMContentLoaded', function() {
  // 获取DOM元素
  const extractBtn = document.getElementById('extractBtn');
  const settingsBtn = document.getElementById('settingsBtn');
  const statusDiv = document.getElementById('status');
  const directoryPathSpan = document.getElementById('directoryPath');
  
  // 加载保存目录和本地服务状态
  loadSettings();
  
  // 添加事件监听器
  extractBtn.addEventListener('click', extractBookInfo);
  settingsBtn.addEventListener('click', openSettings);
  
  // 检测网站类型
  function detectWebsiteType(url) {
    if (url.includes('jd.com')) return 'jd';
    if (url.includes('dangdang.com')) return 'dangdang';
    if (url.includes('douban.com/subject/')) return 'douban';
    if (url.includes('amazon')) return 'amazon';
    return 'unknown';
  }
  
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
    
    // 显示按钮点击反馈
    extractBtn.disabled = true;
    extractBtn.classList.add('processing');
    extractBtn.textContent = '提取中...';
    
    // 获取保存目录
    chrome.storage.local.get(['saveDirectory'], function(result) {
      if (!result.saveDirectory) {
        showStatus('请先在设置中设置保存目录', 'error');
        resetExtractButton();
        return;
      }
      
      // 获取当前标签页
      chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        const activeTab = tabs[0];
        const url = activeTab.url;
        const siteType = detectWebsiteType(url);
        
        if (siteType === 'unknown') {
          showStatus('请在支持的图书页面使用此插件', 'error');
          resetExtractButton();
          return;
        }
        
        // Amazon网站使用原有流程
        if (siteType === 'amazon') {
          // 提取亚马逊图书信息
          chrome.scripting.executeScript({
            target: { tabId: activeTab.id },
            function: function() {
              return document.documentElement.outerHTML;
            }
          }, function(results) {
            if (chrome.runtime.lastError) {
              showStatus('获取页面内容失败: ' + chrome.runtime.lastError.message, 'error');
              resetExtractButton();
              return;
            }
            
            if (!results || !results[0] || !results[0].result) {
              showStatus('无法获取页面内容', 'error');
              resetExtractButton();
              return;
            }
            
            // 获取HTML内容
            const htmlContent = results[0].result;
            
            // 根据URL确定区域
            let region = 'us'; // 默认为美国区域
            if (url.includes('amazon.co.uk')) {
              region = 'uk';
            } else if (url.includes('amazon.co.jp')) {
              region = 'jp';
            }
            
            // 生成文件名
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const fileName = `amazon_${region}_${timestamp}.html`;
            
            // 保存HTML内容并通知处理结果
            showStatus('正在处理HTML内容...', 'info');
            
            chrome.runtime.sendMessage({
              action: 'runPythonScript',
              fileName: fileName,
              htmlContent: htmlContent,
              saveDirectory: result.saveDirectory,
              region: region,
              url: url
            }, function(response) {
              if (response.success) {
                showStatus('提取成功! 已保存到: ' + response.outputFile, 'success');
                
                // 延迟关闭popup
                setTimeout(function() {
                  window.close();
                }, 2000);
              } else {
                showStatus(response.message || '提取失败', 'error');
                resetExtractButton();
              }
            });
          });
        } 
        // 中文网站使用新流程
        else {
          console.log(`准备注入${siteType}提取脚本`);
          
          // 先检查脚本是否已注入
          chrome.tabs.sendMessage(
            activeTab.id, 
            {action: 'ping'}, 
            function(pingResponse) {
              // 如果有错误，可能是脚本未注入
              if (chrome.runtime.lastError || !pingResponse) {
                console.log(`${siteType}提取脚本未注入，开始注入`);
                
                // 注入中文网站提取脚本
                chrome.scripting.executeScript({
                  target: { tabId: activeTab.id },
                  files: [`js/${siteType}_extraction.js`]
                }, function() {
                  if (chrome.runtime.lastError) {
                    console.error('注入脚本失败:', chrome.runtime.lastError.message);
                    showStatus('注入脚本失败: ' + chrome.runtime.lastError.message, 'error');
                    resetExtractButton();
                    return;
                  }
                  
                  console.log(`${siteType}提取脚本注入成功，开始提取信息`);
                  
                  // 执行提取函数 - 给脚本一点加载时间
                  setTimeout(() => {
                    executeExtraction();
                  }, 500);
                });
              } else {
                console.log(`${siteType}提取脚本已存在，直接执行提取`);
                executeExtraction();
              }
            }
          );
          
          // 执行提取函数
          function executeExtraction() {
            chrome.tabs.sendMessage(
              activeTab.id, 
              {action: 'extractInfo', site: siteType}, 
              function(response) {
                if (chrome.runtime.lastError) {
                  console.error('提取失败:', chrome.runtime.lastError.message);
                  showStatus('提取失败: ' + chrome.runtime.lastError.message, 'error');
                  resetExtractButton();
                  return;
                }
                
                if (!response) {
                  showStatus('页面未返回任何数据', 'error');
                  resetExtractButton();
                  return;
                }
                
                if (!response.success || !response.bookInfo) {
                  const errorMsg = response.error || '无法从页面提取图书信息';
                  showStatus(errorMsg, 'error');
                  resetExtractButton();
                  return;
                }
                
                console.log('成功提取图书信息:', response.bookInfo);
                
                // 发送数据到background.js处理
                chrome.runtime.sendMessage({
                  action: 'processChinesesSiteData',
                  data: response.bookInfo,
                  siteType: siteType,
                  url: activeTab.url
                }, function(response) {
                  if (response && response.success) {
                    showStatus(response.message || '提取成功！', 'success');
                    
                    // 成功后延迟关闭popup
                    setTimeout(function() {
                      window.close();
                    }, 1500);
                  } else {
                    showStatus(response && response.message ? response.message : '处理失败', 'error');
                    resetExtractButton();
                  }
                });
              }
            );
          }
        }
      });
    });
  }
  
  // 重置提取按钮
  function resetExtractButton() {
    extractBtn.disabled = false;
    extractBtn.classList.remove('processing');
    extractBtn.textContent = '提取图书信息';
  }
  
  // 显示状态信息
  function showStatus(message, type) {
    statusDiv.innerHTML = type === 'info' && message.includes('正在')
      ? `<p><span class="loading"></span> ${message}</p>`
      : `<p class="${type}">${message}</p>`;
  }
});
