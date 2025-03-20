#!/usr/bin/env python3
"""
Amazon Book Extractor - 服务控制器
提供GUI界面，方便用户管理本地服务
"""

import os
import sys
import time
import json
import socket
import tkinter as tk
import subprocess
import webbrowser
import platform
import signal
import logging
from tkinter import ttk, messagebox, filedialog

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("service_controller.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ServiceController")

# 诊断信息
logger.info("=== 服务控制器启动 ===")
logger.info(f"Python版本: {sys.version}")
logger.info(f"系统平台: {platform.platform()}")
logger.info(f"当前工作目录: {os.getcwd()}")
logger.info(f"脚本目录: {os.path.dirname(os.path.abspath(__file__))}")
logger.info(f"环境变量PATH: {os.environ.get('PATH', '未设置')}")
logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', '未设置')}")
logger.info(f"用户主目录: {os.path.expanduser('~')}")

# 确保使用正确的工作目录
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
logger.info(f"已将工作目录更改为: {script_dir}")

# 脚本路径
SERVICE_SCRIPT = os.path.join(script_dir, "local_service.py")
logger.info(f"服务脚本路径: {SERVICE_SCRIPT}")

# 检查脚本文件是否存在
if not os.path.exists(SERVICE_SCRIPT):
    logger.error(f"服务脚本文件不存在: {SERVICE_SCRIPT}")
    print(f"错误: 服务脚本文件不存在: {SERVICE_SCRIPT}")
    sys.exit(1)

# 服务配置
CONFIG_FILE = "service_config.json"
DEFAULT_PORT = 5001

# 导入模块
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    logger.warning("psutil库未安装，将使用备用方法查找进程")
    HAS_PSUTIL = False

class ServiceController:
    def __init__(self, root):
        self.root = root
        self.root.title("Amazon Book Extractor 服务控制器")
        self.root.geometry("550x450")  # 增加窗口大小
        self.root.resizable(True, True)  # 允许调整大小
        
        # 设置窗口关闭事件处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 设置窗口图标(如果有)
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # 初始化变量
        self.process = None
        self.config = self.load_config()
        self.status_var = tk.StringVar(value="未运行")
        self.port_var = tk.StringVar(value=str(self.config.get("port", DEFAULT_PORT)))
        self.save_dir_var = tk.StringVar(value=self.config.get("save_directory", ""))
        self.webhook_var = tk.StringVar(value=self.config.get("feishu_webhook", ""))
        
        # 创建界面
        self.create_widgets()
        
        # 检查服务是否已经在运行
        self.check_service_status()
        
        # 定期检查服务状态
        self.root.after(2000, self.update_status)

    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="Amazon Book Extractor 服务控制", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # 服务状态框架
        status_frame = ttk.LabelFrame(main_frame, text="服务状态", padding=10)
        status_frame.pack(fill=tk.X, pady=5)
        
        # 状态显示
        status_row = ttk.Frame(status_frame)
        status_row.pack(fill=tk.X)
        
        ttk.Label(status_row, text="当前状态:").pack(side=tk.LEFT, padx=5)
        
        self.status_indicator = ttk.Label(status_row, textvariable=self.status_var, font=("Arial", 10, "bold"))
        self.status_indicator.pack(side=tk.LEFT, padx=5)
        
        # 设置框架
        settings_frame = ttk.LabelFrame(main_frame, text="服务设置", padding=10)
        settings_frame.pack(fill=tk.X, pady=5)
        
        # 端口设置
        port_row = ttk.Frame(settings_frame)
        port_row.pack(fill=tk.X, pady=2)
        
        ttk.Label(port_row, text="端口:").pack(side=tk.LEFT, padx=5)
        port_entry = ttk.Entry(port_row, textvariable=self.port_var, width=10)
        port_entry.pack(side=tk.LEFT, padx=5)
        
        # 保存目录设置
        dir_row = ttk.Frame(settings_frame)
        dir_row.pack(fill=tk.X, pady=2)
        
        ttk.Label(dir_row, text="保存目录:").pack(side=tk.LEFT, padx=5)
        dir_entry = ttk.Entry(dir_row, textvariable=self.save_dir_var, width=40)
        dir_entry.pack(side=tk.LEFT, padx=5)
        
        # Webhook设置
        webhook_row = ttk.Frame(settings_frame)
        webhook_row.pack(fill=tk.X, pady=2)
        
        ttk.Label(webhook_row, text="飞书Webhook:").pack(side=tk.LEFT, padx=5)
        webhook_entry = ttk.Entry(webhook_row, textvariable=self.webhook_var, width=40)
        webhook_entry.pack(side=tk.LEFT, padx=5)
        
        # 保存设置按钮
        save_btn = ttk.Button(settings_frame, text="保存设置", command=self.save_settings)
        save_btn.pack(anchor=tk.E, pady=5)
        
        # 控制按钮框架 - 使用标签框架
        control_frame = ttk.LabelFrame(main_frame, text="服务控制")
        control_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # 按钮容器
        btn_container = ttk.Frame(control_frame)
        btn_container.pack(fill=tk.X, pady=5, padx=5)
        
        # 使用网格布局来确保按钮平均分布
        # 启动按钮
        self.start_btn = ttk.Button(btn_container, text="启动服务", command=self.start_service)
        self.start_btn.grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        
        # 重启按钮
        self.restart_btn = ttk.Button(btn_container, text="重启服务", command=self.restart_service)
        self.restart_btn.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        # 停止按钮
        self.stop_btn = ttk.Button(btn_container, text="停止服务", command=self.stop_service)
        self.stop_btn.grid(row=0, column=2, padx=5, pady=5, sticky='ew')
        
        # 打开页面按钮
        self.open_btn = ttk.Button(btn_container, text="打开页面", command=self.open_status_page)
        self.open_btn.grid(row=0, column=3, padx=5, pady=5, sticky='ew')
        
        # 配置列权重，使按钮均匀分布
        for i in range(4):
            btn_container.columnconfigure(i, weight=1)
        
        # 开机自启
        auto_frame = ttk.Frame(main_frame)
        auto_frame.pack(fill=tk.X, pady=5)
        
        self.autostart_var = tk.BooleanVar(value=False)
        autostart_check = ttk.Checkbutton(auto_frame, text="开机自动启动服务", variable=self.autostart_var, command=self.toggle_autostart)
        autostart_check.pack(side=tk.LEFT, padx=5)
        
        # 检查是否已设置自启动
        self.check_autostart()
        
        # 底部状态栏
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        ttk.Label(footer_frame, text="© Amazon Book Extractor").pack(side=tk.LEFT)
        
    def load_config(self):
        """加载服务配置"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"port": DEFAULT_PORT, "save_directory": "", "feishu_webhook": ""}
    
    def save_settings(self):
        """保存服务设置"""
        try:
            # 更新配置
            self.config["port"] = int(self.port_var.get())
            self.config["save_directory"] = self.save_dir_var.get()
            self.config["feishu_webhook"] = self.webhook_var.get()
            
            # 写入配置文件
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("成功", "设置已保存")
            
            # 如果服务正在运行，提示重启
            if self.process is not None and self.process.poll() is None:
                if messagebox.askyesno("重启服务", "设置已更改，是否要重启服务以应用新设置？"):
                    self.restart_service()
                    
        except Exception as e:
            messagebox.showerror("错误", f"保存设置失败: {str(e)}")
    
    def find_service_process(self):
        """查找服务进程"""
        try:
            # 尝试使用psutil库
            if HAS_PSUTIL:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    if proc.info['cmdline'] and len(proc.info['cmdline']) > 1:
                        cmdline = ' '.join(proc.info['cmdline'])
                        if SERVICE_SCRIPT in cmdline and '--port' in cmdline:
                            logger.info(f"找到服务进程: PID={proc.info['pid']}")
                            return proc
            else:
                # 备用方法：使用命令行工具
                if sys.platform == 'darwin' or sys.platform.startswith('linux'):
                    # macOS 或 Linux
                    result = subprocess.run(
                        ['pgrep', '-f', SERVICE_SCRIPT], 
                        stdout=subprocess.PIPE, 
                        text=True
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        pid = int(result.stdout.strip().split('\n')[0])
                        logger.info(f"通过pgrep找到服务进程: PID={pid}")
                        # 创建一个类似psutil.Process的对象，但只实现我们需要的方法
                        class SimpleProcess:
                            def __init__(self, pid):
                                self.pid = pid
                            
                            def is_running(self):
                                return self._check_running()
                            
                            def _check_running(self):
                                try:
                                    # 发送信号0来检查进程是否存在
                                    os.kill(self.pid, 0)
                                    return True
                                except OSError:
                                    return False
                            
                            def terminate(self):
                                try:
                                    if sys.platform == 'darwin':
                                        subprocess.run(['kill', str(self.pid)])
                                    else:
                                        os.kill(self.pid, signal.SIGTERM)
                                    return True
                                except:
                                    return False
                        
                        return SimpleProcess(pid)
                else:
                    # Windows
                    result = subprocess.run(
                        ['tasklist', '/FI', f'IMAGENAME eq python*', '/FO', 'CSV'], 
                        stdout=subprocess.PIPE, 
                        text=True
                    )
                    if SERVICE_SCRIPT in result.stdout:
                        for line in result.stdout.splitlines():
                            if SERVICE_SCRIPT in line:
                                parts = line.strip('"').split('","')
                                if len(parts) >= 2:
                                    pid = int(parts[1])
                                    logger.info(f"通过tasklist找到服务进程: PID={pid}")
                                    # 返回简单进程对象
                                    return SimpleProcess(pid)
                                
            return None
        except Exception as e:
            logger.error(f"查找服务进程时出错: {str(e)}")
            return None
    
    def check_service_status(self):
        """检查服务状态"""
        if self.process is not None and self.process.poll() is None:
            # 进程存在并运行
            self.status_var.set("运行中")
            self.status_indicator.config(foreground="green")
            self.update_button_states(running=True)
            return True
        
        # 检查是否有其他实例运行
        proc = self.find_service_process()
        if proc:
            self.process = None  # 重置当前进程引用
            self.status_var.set(f"运行中 (PID: {proc.pid})")
            self.status_indicator.config(foreground="green")
            self.update_button_states(running=True)
            return True
        
        # 服务未运行
        self.status_var.set("未运行")
        self.status_indicator.config(foreground="red")
        self.update_button_states(running=False)
        return False
    
    def update_status(self):
        """定期更新状态"""
        self.check_service_status()
        self.root.after(5000, self.update_status)  # 每5秒检查一次
    
    def update_button_states(self, running=False):
        """更新按钮状态"""
        if running:
            self.start_btn.config(state=tk.DISABLED)
            self.restart_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.NORMAL)
            self.open_btn.config(state=tk.NORMAL)
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.restart_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
            self.open_btn.config(state=tk.DISABLED)
    
    def start_service(self):
        """启动服务"""
        try:
            # 检查是否已经在运行
            if self.check_service_status():
                messagebox.showinfo("提示", "服务已经在运行")
                return
            
            # 验证保存目录
            save_dir = self.save_dir_var.get()
            if save_dir:
                # 检查目录是否存在，如果不存在则尝试创建
                if not os.path.exists(save_dir):
                    try:
                        os.makedirs(save_dir, exist_ok=True)
                        print(f"已创建目录: {save_dir}")
                    except Exception as e:
                        error_msg = f"创建保存目录失败: {str(e)}"
                        print(error_msg)
                        messagebox.showerror("错误", error_msg)
                        return
                
                # 检查目录写入权限
                try:
                    test_file = os.path.join(save_dir, ".test_write_permission")
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                except Exception as e:
                    error_msg = f"保存目录没有写入权限: {str(e)}"
                    print(error_msg)
                    messagebox.showerror("错误", error_msg)
                    return
                
                # 对包含空格和特殊字符的iCloud路径进行特殊处理
                if "Mobile Documents" in save_dir or "com~apple~CloudDocs" in save_dir:
                    print(f"检测到iCloud路径: {save_dir}")
                    # 确保路径格式正确
                    save_dir = save_dir.replace("\\", "/")
            
            # 构建命令行参数
            cmd = [sys.executable, SERVICE_SCRIPT, 
                  "--port", self.port_var.get()]
            
            if save_dir:
                cmd.extend(["--directory", save_dir])
            
            cmd.append("--no-browser")  # 由控制器管理浏览器
            
            if self.webhook_var.get():
                cmd.extend(["--webhook", self.webhook_var.get()])
            
            print(f"启动命令: {' '.join(cmd)}")
            
            # 启动服务
            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待服务启动
            time.sleep(2)
            
            # 检查是否成功启动
            if self.process.poll() is None:
                self.status_var.set("运行中")
                self.status_indicator.config(foreground="green")
                self.update_button_states(running=True)
                messagebox.showinfo("成功", "服务已启动")
            else:
                # 获取错误输出
                _, stderr = self.process.communicate(timeout=1)
                error_msg = f"服务启动失败: {stderr}"
                print(error_msg)
                messagebox.showerror("错误", error_msg)
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"启动服务时发生错误: {str(e)}\n{error_details}")
            messagebox.showerror("错误", f"启动服务失败: {str(e)}")
    
    def stop_service(self):
        """停止服务"""
        try:
            stopped = False
            
            # 尝试使用当前进程引用
            if self.process is not None and self.process.poll() is None:
                print(f"正在终止当前进程: {self.process.pid}")
                self.process.terminate()
                # 等待进程结束
                for _ in range(10):
                    if self.process.poll() is not None:
                        stopped = True
                        break
                    time.sleep(0.5)
                
                # 如果仍未结束，强制终止
                if self.process.poll() is None:
                    print(f"进程未响应终止信号，正在强制终止: {self.process.pid}")
                    self.process.kill()
                    stopped = True
                
                self.process = None
            else:
                # 查找并终止其他实例
                proc = self.find_service_process()
                if proc:
                    print(f"正在终止外部进程: {proc.pid}")
                    try:
                        proc.terminate()
                        time.sleep(1)
                        if proc.is_running():
                            print(f"进程未响应终止信号，正在强制终止: {proc.pid}")
                            proc.kill()
                        stopped = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                        print(f"终止进程时发生错误: {e}")
            
            # 在macOS上，可能需要额外的清理
            if sys.platform == 'darwin':
                # 尝试查找并杀死所有相关的Python进程
                try:
                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                        if proc.info['name'] == 'Python' or proc.info['name'] == 'python' or proc.info['name'] == 'python3':
                            cmd = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                            if SERVICE_SCRIPT in cmd:
                                print(f"正在终止macOS上的Python进程: {proc.pid}")
                                proc.terminate()
                                time.sleep(0.5)
                                if proc.is_running():
                                    proc.kill()
                                stopped = True
                except Exception as e:
                    print(f"清理macOS进程时发生错误: {e}")
            
            # 更新状态
            self.status_var.set("未运行")
            self.status_indicator.config(foreground="red")
            self.update_button_states(running=False)
            
            if stopped:
                messagebox.showinfo("成功", "服务已停止")
            else:
                messagebox.showinfo("提示", "没有找到正在运行的服务")
            
        except Exception as e:
            messagebox.showerror("错误", f"停止服务失败: {str(e)}")
            print(f"停止服务时发生错误: {e}")
            import traceback
            print(traceback.format_exc())
    
    def restart_service(self):
        """重启服务"""
        self.stop_service()
        time.sleep(1)  # 等待服务完全停止
        self.start_service()
    
    def open_status_page(self):
        """打开服务状态页面"""
        port = self.port_var.get()
        webbrowser.open(f"http://localhost:{port}/")
    
    def toggle_autostart(self):
        """切换开机自启动"""
        try:
            if self.autostart_var.get():
                self.set_autostart()
            else:
                self.remove_autostart()
        except Exception as e:
            messagebox.showerror("错误", f"设置自启动失败: {str(e)}")
            self.autostart_var.set(not self.autostart_var.get())  # 恢复状态
    
    def set_autostart(self):
        """设置开机自启动"""
        if sys.platform == 'win32':
            # Windows平台使用注册表或快捷方式
            import winreg
            startup_path = os.path.join(os.environ["APPDATA"], 
                                       r"Microsoft\Windows\Start Menu\Programs\Startup")
            bat_path = os.path.join(startup_path, "Amazon_Book_Extractor.bat")
            
            # 创建启动脚本
            with open(bat_path, 'w') as f:
                script_path = os.path.abspath(sys.argv[0])
                f.write(f'@echo off\n"{sys.executable}" "{script_path}"\n')
            
            messagebox.showinfo("成功", "已设置开机自启动")
        
        elif sys.platform == 'darwin':
            # macOS平台使用launchd
            plist_path = os.path.expanduser("~/Library/LaunchAgents/com.amazon.bookextractor.plist")
            
            # 创建plist文件
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.amazon.bookextractor</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{os.path.abspath(sys.argv[0])}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>"""
            
            with open(plist_path, 'w') as f:
                f.write(plist_content)
            
            # 注册启动项
            subprocess.run(["launchctl", "load", plist_path])
            
            messagebox.showinfo("成功", "已设置开机自启动")
        
        else:
            # Linux平台使用systemd或桌面自启动
            autostart_dir = os.path.expanduser("~/.config/autostart")
            if not os.path.exists(autostart_dir):
                os.makedirs(autostart_dir)
            
            desktop_path = os.path.join(autostart_dir, "amazon-book-extractor.desktop")
            
            desktop_content = f"""[Desktop Entry]
Type=Application
Name=Amazon Book Extractor
Exec={sys.executable} {os.path.abspath(sys.argv[0])}
Terminal=false
X-GNOME-Autostart-enabled=true
"""
            
            with open(desktop_path, 'w') as f:
                f.write(desktop_content)
            
            messagebox.showinfo("成功", "已设置开机自启动")
    
    def remove_autostart(self):
        """移除开机自启动"""
        if sys.platform == 'win32':
            # Windows平台
            startup_path = os.path.join(os.environ["APPDATA"], 
                                       r"Microsoft\Windows\Start Menu\Programs\Startup")
            bat_path = os.path.join(startup_path, "Amazon_Book_Extractor.bat")
            
            if os.path.exists(bat_path):
                os.remove(bat_path)
            
            messagebox.showinfo("成功", "已移除开机自启动")
            
        elif sys.platform == 'darwin':
            # macOS平台
            plist_path = os.path.expanduser("~/Library/LaunchAgents/com.amazon.bookextractor.plist")
            
            if os.path.exists(plist_path):
                # 卸载启动项
                subprocess.run(["launchctl", "unload", plist_path])
                os.remove(plist_path)
            
            messagebox.showinfo("成功", "已移除开机自启动")
            
        else:
            # Linux平台
            desktop_path = os.path.expanduser("~/.config/autostart/amazon-book-extractor.desktop")
            
            if os.path.exists(desktop_path):
                os.remove(desktop_path)
            
            messagebox.showinfo("成功", "已移除开机自启动")
    
    def check_autostart(self):
        """检查是否已设置自启动"""
        if sys.platform == 'win32':
            # Windows平台
            startup_path = os.path.join(os.environ["APPDATA"], 
                                       r"Microsoft\Windows\Start Menu\Programs\Startup")
            bat_path = os.path.join(startup_path, "Amazon_Book_Extractor.bat")
            
            self.autostart_var.set(os.path.exists(bat_path))
            
        elif sys.platform == 'darwin':
            # macOS平台
            plist_path = os.path.expanduser("~/Library/LaunchAgents/com.amazon.bookextractor.plist")
            self.autostart_var.set(os.path.exists(plist_path))
            
        else:
            # Linux平台
            desktop_path = os.path.expanduser("~/.config/autostart/amazon-book-extractor.desktop")
            self.autostart_var.set(os.path.exists(desktop_path))

    def on_closing(self):
        """窗口关闭时的处理"""
        try:
            # 如果服务正在运行，询问是否停止服务
            if self.check_service_status():
                if messagebox.askyesno("退出确认", "服务正在运行，是否停止服务并退出？"):
                    self.stop_service()
                    time.sleep(0.5)  # 给服务一点时间停止
                else:
                    if messagebox.askyesno("退出确认", "服务将继续在后台运行，确定要退出控制器吗？"):
                        pass  # 继续退出
                    else:
                        return  # 取消退出
            
            # 保存当前设置
            self.save_config_silently()
            
            # 销毁窗口并退出
            self.root.destroy()
            sys.exit(0)
        except Exception as e:
            print(f"关闭时发生错误: {e}")
            self.root.destroy()
            sys.exit(1)
            
    def save_config_silently(self):
        """静默保存配置，不显示消息框"""
        try:
            # 更新配置
            self.config["port"] = int(self.port_var.get())
            self.config["save_directory"] = self.save_dir_var.get()
            self.config["feishu_webhook"] = self.webhook_var.get()
            
            # 写入配置文件
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

def main():
    # 创建主窗口
    root = tk.Tk()
    
    # 设置窗口样式
    style = ttk.Style()
    if sys.platform == 'win32':
        style.theme_use('vista')
    
    # 创建应用
    app = ServiceController(root)
    
    # 启动主循环
    root.mainloop()

if __name__ == "__main__":
    main() 