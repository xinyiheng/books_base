/**
 * Amazon Book Info Extractor - Settings Script
 * 处理设置页面的功能
 */

document.addEventListener('DOMContentLoaded', function() {
  // 获取DOM元素
  const saveDirectoryInput = document.getElementById('saveDirectory');
  const feishuWebhookInput = document.getElementById('feishuWebhook');
  const localServiceEnabledCheckbox = document.getElementById('localServiceEnabled');
  const localServiceUrlInput = document.getElementById('localServiceUrl');
  const cloudServiceEnabledCheckbox = document.getElementById('cloudServiceEnabled'); 
  const cloudServiceUrlInput = document.getElementById('cloudServiceUrl'); 
  const autoExtractEnabledCheckbox = document.getElementById('autoExtractEnabled');
  const saveBtn = document.getElementById('saveBtn');
  const cancelBtn = document.getElementById('cancelBtn');
  const createDirectoriesBtn = document.getElementById('createDirectoriesBtn');
  const testConnectionBtn = document.getElementById('testConnectionBtn');
  const syncToCloudBtn = document.getElementById('syncToCloudBtn'); 
  const syncFromCloudBtn = document.getElementById('syncFromCloudBtn'); 
  const saveStatusDiv = document.getElementById('saveStatus');
  const directoryStatusDiv = document.getElementById('directoryStatus');
  const connectionStatusDiv = document.getElementById('connectionStatus');
  const serviceStatusDiv = document.getElementById('serviceStatus');
  const syncStatusDiv = document.getElementById('syncStatus'); 
  
  // 加载设置
  loadSettings();
  
  // 添加事件监听器
  saveBtn.addEventListener('click', saveSettings);
  cancelBtn.addEventListener('click', function() {
    window.close();
  });
  createDirectoriesBtn.addEventListener('click', createDirectories);
  testConnectionBtn.addEventListener('click', testServiceConnection);
  syncToCloudBtn.addEventListener('click', syncToCloud); 
  syncFromCloudBtn.addEventListener('click', syncFromCloud); 
  localServiceEnabledCheckbox.addEventListener('change', updateServiceStatus);
  cloudServiceEnabledCheckbox.addEventListener('change', updateServiceStatus); 
  
  // 加载设置
  function loadSettings() {
    chrome.storage.local.get(['saveDirectory', 'feishuWebhook', 'localService', 'autoExtract'], function(result) {
      if (result.saveDirectory) {
        saveDirectoryInput.value = result.saveDirectory;
      }
      
      if (result.feishuWebhook) {
        feishuWebhookInput.value = result.feishuWebhook;
      } else {
        // 设置默认飞书webhook URL
        feishuWebhookInput.value = 'https://thc4xpukay.feishu.cn/base/automation/webhook/event/NiSSacYBNwta2shHV9Acyf08nlh';
      }
      
      if (result.localService) {
        localServiceEnabledCheckbox.checked = result.localService.enabled;
        localServiceUrlInput.value = result.localService.url || 'http://localhost:5001';
        
        // 加载云服务设置
        cloudServiceEnabledCheckbox.checked = result.localService.useCloud || false;
        cloudServiceUrlInput.value = result.localService.cloudUrl || '';
        
        updateServiceStatus(result.localService.status || 'unknown');
      } else {
        localServiceUrlInput.value = 'http://localhost:5001';
      }
      
      // 加载自动提取设置，默认为启用
      autoExtractEnabledCheckbox.checked = result.autoExtract !== undefined ? result.autoExtract : true;
    });
  }
  
  // 保存设置
  function saveSettings() {
    const saveDirectory = saveDirectoryInput.value.trim();
    const feishuWebhook = feishuWebhookInput.value.trim();
    const localServiceEnabled = localServiceEnabledCheckbox.checked;
    const localServiceUrl = localServiceUrlInput.value.trim();
    const cloudServiceEnabled = cloudServiceEnabledCheckbox.checked;
    const cloudServiceUrl = cloudServiceUrlInput.value.trim();
    const autoExtract = autoExtractEnabledCheckbox.checked;
    
    // 验证输入
    if (!saveDirectory) {
      showSaveStatus('请输入保存目录', 'error');
      return;
    }
    
    if (localServiceEnabled && !localServiceUrl) {
      showSaveStatus('请输入本地服务URL', 'error');
      return;
    }
    
    if (cloudServiceEnabled && !cloudServiceUrl) {
      showSaveStatus('请输入云服务URL', 'error');
      return;
    }
    
    // 如果服务已启用，先测试连接
    if (localServiceEnabled || cloudServiceEnabled) {
      const config = {
        enabled: localServiceEnabled || cloudServiceEnabled,
        url: localServiceUrl,
        cloudUrl: cloudServiceUrl,
        useCloud: cloudServiceEnabled
      };
      
      console.log('正在测试服务连接...');
      showConnectionStatus('正在测试连接...', 'info');
      
      chrome.runtime.sendMessage({
        action: 'setLocalServiceConfig',
        config: config
      }, function(response) {
        console.log('服务连接测试结果:', response);
        
        if (response && response.success) {
          const status = response.config.status;
          
          // 保存设置，包括连接状态
          chrome.storage.local.set({
            saveDirectory: saveDirectory,
            feishuWebhook: feishuWebhook,
            localService: response.config,
            autoExtract: autoExtract
          }, function() {
            showSaveStatus('设置已保存', 'success');
            
            if (status === 'connected') {
              showConnectionStatus('已连接到服务', 'success');
              
              // 同步配置到服务
              syncConfigToService(saveDirectory, feishuWebhook, response.config);
            } else {
              showConnectionStatus('无法连接到服务', 'error');
            }
          });
        } else {
          // 如果测试连接失败，仍然保存其他设置
          chrome.storage.local.set({
            saveDirectory: saveDirectory,
            feishuWebhook: feishuWebhook,
            localService: {
              enabled: localServiceEnabled || cloudServiceEnabled,
              url: localServiceUrl,
              cloudUrl: cloudServiceUrl,
              useCloud: cloudServiceEnabled,
              status: 'disconnected'
            },
            autoExtract: autoExtract
          }, function() {
            showSaveStatus('设置已保存，但无法连接到服务', 'warning');
            showConnectionStatus('无法连接到服务', 'error');
          });
        }
      });
    } else {
      // 如果服务未启用，直接保存设置
      chrome.storage.local.set({
        saveDirectory: saveDirectory,
        feishuWebhook: feishuWebhook,
        localService: {
          enabled: false,
          url: localServiceUrl,
          cloudUrl: cloudServiceUrl,
          useCloud: false,
          status: 'disconnected'
        },
        autoExtract: autoExtract
      }, function() {
        showSaveStatus('设置已保存', 'success');
      });
    }
  }
  
  // 同步配置到服务
  function syncConfigToService(saveDirectory, feishuWebhook, serviceConfig) {
    const configData = {
      save_directory: saveDirectory
    };
    
    if (feishuWebhook) {
      configData.feishu_webhook = feishuWebhook;
    }
    
    // 确定要使用的URL
    const serviceUrl = serviceConfig.useCloud && serviceConfig.cloudUrl 
      ? serviceConfig.cloudUrl 
      : serviceConfig.url;
    
    // 发送配置到服务
    fetch(`${serviceUrl}/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(configData)
    })
    .then(response => response.json())
    .then(data => {
      console.log('配置已同步到服务:', data);
      showSaveStatus('配置已同步到服务', 'success');
    })
    .catch(error => {
      console.error('同步配置到服务失败:', error);
      showSaveStatus('同步配置到服务失败，请确保服务正在运行', 'error');
    });
  }
  
  // 从本地同步到云端
  function syncToCloud() {
    const saveDirectory = saveDirectoryInput.value.trim();
    
    if (!saveDirectory) {
      showStatus(syncStatusDiv, '请先输入保存目录', 'error');
      return;
    }
    
    // 确定要使用的服务URL
    let serviceUrl = '';
    let isCloud = false;
    
    chrome.storage.local.get(['localService'], function(result) {
      if (result.localService) {
        if (result.localService.useCloud && result.localService.cloudUrl) {
          serviceUrl = result.localService.cloudUrl;
          isCloud = true;
        } else if (result.localService.enabled && result.localService.url) {
          serviceUrl = result.localService.url;
        }
      }
      
      if (!serviceUrl) {
        showStatus(syncStatusDiv, '请先配置并启用本地服务或云服务', 'error');
        return;
      }
      
      showStatus(syncStatusDiv, '正在从本地同步数据到云端...', 'info');
      
      // 发送同步请求
      fetch(`${serviceUrl}/sync-data`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sync_type: 'local_to_cloud',
          local_directory: saveDirectory
        })
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          showStatus(syncStatusDiv, data.message, 'success');
        } else {
          showStatus(syncStatusDiv, `同步失败: ${data.message}`, 'error');
        }
      })
      .catch(error => {
        console.error('同步数据到云端失败:', error);
        showStatus(syncStatusDiv, `同步失败: ${error.message}`, 'error');
      });
    });
  }
  
  // 从云端同步到本地
  function syncFromCloud() {
    const saveDirectory = saveDirectoryInput.value.trim();
    
    if (!saveDirectory) {
      showStatus(syncStatusDiv, '请先输入保存目录', 'error');
      return;
    }
    
    // 确定要使用的服务URL
    let serviceUrl = '';
    let isCloud = false;
    
    chrome.storage.local.get(['localService'], function(result) {
      if (result.localService) {
        if (result.localService.useCloud && result.localService.cloudUrl) {
          serviceUrl = result.localService.cloudUrl;
          isCloud = true;
        } else if (result.localService.enabled && result.localService.url) {
          serviceUrl = result.localService.url;
        }
      }
      
      if (!serviceUrl) {
        showStatus(syncStatusDiv, '请先配置并启用本地服务或云服务', 'error');
        return;
      }
      
      showStatus(syncStatusDiv, '正在从云端同步数据到本地...', 'info');
      
      // 发送同步请求
      fetch(`${serviceUrl}/sync-data`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sync_type: 'cloud_to_local',
          local_directory: saveDirectory
        })
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          showStatus(syncStatusDiv, data.message, 'success');
        } else {
          showStatus(syncStatusDiv, `同步失败: ${data.message}`, 'error');
        }
      })
      .catch(error => {
        console.error('从云端同步数据失败:', error);
        showStatus(syncStatusDiv, `同步失败: ${error.message}`, 'error');
      });
    });
  }
  
  // 创建必要的目录
  function createDirectories() {
    const saveDirectory = saveDirectoryInput.value.trim();
    
    if (!saveDirectory) {
      showStatus(directoryStatusDiv, '请先输入保存目录', 'error');
      return;
    }
    
    showStatus(directoryStatusDiv, '正在创建目录...', 'info');
    
    // 检查是否启用了本地服务
    chrome.storage.local.get(['localService'], function(result) {
      const localService = result.localService || { enabled: false };
      
      // 发送消息到后台脚本创建目录
      chrome.runtime.sendMessage(
        {
          action: 'createDirectories',
          saveDirectory: saveDirectory
        },
        function(response) {
          if (response.success) {
            showStatus(directoryStatusDiv, response.message, 'success');
          } else {
            showStatus(directoryStatusDiv, response.message, 'error');
          }
        }
      );
    });
  }
  
  // 测试服务连接
  function testServiceConnection() {
    const localServiceEnabled = localServiceEnabledCheckbox.checked;
    const localServiceUrl = localServiceUrlInput.value.trim();
    const cloudServiceEnabled = cloudServiceEnabledCheckbox.checked;
    const cloudServiceUrl = cloudServiceUrlInput.value.trim();
    
    if (!localServiceEnabled && !cloudServiceEnabled) {
      showConnectionStatus('请先启用本地服务或云服务', 'warning');
      return;
    }
    
    if (localServiceEnabled && !localServiceUrl) {
      showConnectionStatus('请输入本地服务URL', 'error');
      return;
    }
    
    if (cloudServiceEnabled && !cloudServiceUrl) {
      showConnectionStatus('请输入云服务URL', 'error');
      return;
    }
    
    showConnectionStatus('正在测试连接...', 'info');
    
    const config = {
      enabled: localServiceEnabled || cloudServiceEnabled,
      url: localServiceUrl,
      cloudUrl: cloudServiceUrl,
      useCloud: cloudServiceEnabled
    };
    
    chrome.runtime.sendMessage({
      action: 'setLocalServiceConfig',
      config: config
    }, function(response) {
      console.log('服务连接测试结果:', response);
      
      if (response && response.success) {
        const status = response.config.status;
        
        if (status === 'connected') {
          showConnectionStatus('已成功连接到服务', 'success');
          updateServiceStatus('connected');
        } else {
          showConnectionStatus('无法连接到服务，请检查URL和服务状态', 'error');
          updateServiceStatus('disconnected');
        }
      } else {
        showConnectionStatus('连接测试失败，请检查浏览器控制台获取更多信息', 'error');
        updateServiceStatus('unknown');
      }
    });
  }
  
  // 更新服务状态
  function updateServiceStatus(status) {
    serviceStatusDiv.className = 'service-status';
    
    if (!localServiceEnabledCheckbox.checked && !cloudServiceEnabledCheckbox.checked) {
      serviceStatusDiv.classList.add('status-disabled');
      serviceStatusDiv.textContent = '已禁用';
      return;
    }
    
    switch (status) {
      case 'connected':
        serviceStatusDiv.classList.add('status-connected');
        serviceStatusDiv.textContent = '已连接';
        break;
      case 'disconnected':
        serviceStatusDiv.classList.add('status-disconnected');
        serviceStatusDiv.textContent = '未连接';
        break;
      default:
        serviceStatusDiv.classList.add('status-unknown');
        serviceStatusDiv.textContent = '未知';
    }
    
    // 保存状态到存储
    chrome.storage.local.get(['localService'], function(result) {
      const localService = result.localService || { enabled: false, url: 'http://localhost:5001' };
      localService.status = status;
      
      chrome.storage.local.set({ localService: localService });
    });
  }
  
  // 显示状态消息
  function showStatus(element, message, type) {
    element.textContent = message;
    element.className = 'status';
    element.classList.add(type);
    element.style.display = 'block';
    
    // 如果是成功消息，3秒后自动隐藏
    if (type === 'success' && element !== directoryStatusDiv) {
      setTimeout(() => {
        element.style.display = 'none';
      }, 3000);
    }
  }
  
  // 显示保存状态消息
  function showSaveStatus(message, type) {
    saveStatusDiv.textContent = message;
    saveStatusDiv.className = 'status';
    saveStatusDiv.classList.add(type);
    saveStatusDiv.style.display = 'block';
    
    // 如果是成功消息，3秒后自动隐藏
    if (type === 'success') {
      setTimeout(() => {
        saveStatusDiv.style.display = 'none';
      }, 3000);
    }
  }
  
  // 显示连接状态消息
  function showConnectionStatus(message, type) {
    connectionStatusDiv.textContent = message;
    connectionStatusDiv.className = 'status';
    connectionStatusDiv.classList.add(type);
    connectionStatusDiv.style.display = 'block';
    
    // 如果是成功消息，3秒后自动隐藏
    if (type === 'success') {
      setTimeout(() => {
        connectionStatusDiv.style.display = 'none';
      }, 3000);
    }
  }
});
