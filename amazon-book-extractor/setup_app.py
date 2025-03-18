#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import subprocess
import sys

# 应用程序名称
APP_NAME = "AmazonBookService"

def create_mac_app():
    """创建Mac应用程序"""
    # 应用程序路径
    app_path = f"/Applications/{APP_NAME}.app"
    
    # 创建应用程序框架
    if os.path.exists(app_path):
        print(f"删除旧的应用程序: {app_path}")
        shutil.rmtree(app_path)
    
    # 创建目录结构
    os.makedirs(f"{app_path}/Contents/MacOS")
    
    # 复制图标 (可选)
    # shutil.copyfile("icon.icns", f"{app_path}/Contents/Resources/icon.icns")
    
    # 创建Info.plist
    with open(f"{app_path}/Contents/Info.plist", "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>{APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>com.amazonbooks.service</string>
    <key>CFBundleName</key>
    <string>{APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
</dict>
</plist>""")
    
    # 创建启动脚本
    script_path = f"{app_path}/Contents/MacOS/{APP_NAME}"
    with open(script_path, "w") as f:
        f.write(f"""#!/bin/bash
osascript -e 'tell application "Terminal" to do script "cd {os.getcwd()} && python service_manager.py start"'
""")
    
    # 添加执行权限
    os.chmod(script_path, 0o755)
    
    print(f"应用程序已创建: {app_path}")
    print("您可以在应用程序目录中找到它，双击即可启动服务")

def create_dock_icons():
    """创建Dock图标"""
    # 创建启动脚本
    start_script = os.path.join(os.getcwd(), "start_service.command")
    with open(start_script, "w") as f:
        f.write(f"""#!/bin/bash
cd {os.getcwd()}
python service_manager.py start
""")
    
    # 创建停止脚本
    stop_script = os.path.join(os.getcwd(), "stop_service.command")
    with open(stop_script, "w") as f:
        f.write(f"""#!/bin/bash
cd {os.getcwd()}
python service_manager.py stop
""")
    
    # 添加执行权限
    os.chmod(start_script, 0o755)
    os.chmod(stop_script, 0o755)
    
    print(f"启动脚本已创建: {start_script}")
    print(f"停止脚本已创建: {stop_script}")
    print("您可以将这些脚本拖到Dock栏，便于快速访问")

def create_launchd_service():
    """创建开机自启动服务"""
    plist_path = os.path.expanduser("~/Library/LaunchAgents/com.amazonbooks.service.plist")
    
    with open(plist_path, "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.amazonbooks.service</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python</string>
        <string>{os.path.join(os.getcwd(), 'local_service.py')}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>{os.getcwd()}</string>
    <key>StandardOutPath</key>
    <string>{os.path.join(os.getcwd(), 'service.log')}</string>
    <key>StandardErrorPath</key>
    <string>{os.path.join(os.getcwd(), 'service_error.log')}</string>
</dict>
</plist>""")
    
    print(f"LaunchAgent配置已创建: {plist_path}")
    print("要启用自动启动，请运行命令:")
    print(f"  launchctl load {plist_path}")
    print("要禁用自动启动，请运行命令:")
    print(f"  launchctl unload {plist_path}")

def main():
    print("===== Amazon Book Service 安装工具 =====")
    print("请选择要创建的项目:")
    print("1. 创建Mac应用程序")
    print("2. 创建Dock图标")
    print("3. 创建开机自启动服务")
    print("4. 全部创建")
    print("0. 退出")
    
    choice = input("请输入选项编号: ")
    
    if choice == "1":
        create_mac_app()
    elif choice == "2":
        create_dock_icons()
    elif choice == "3":
        create_launchd_service()
    elif choice == "4":
        create_mac_app()
        create_dock_icons()
        create_launchd_service()
    elif choice == "0":
        print("已退出")
    else:
        print("无效的选择，请重新运行脚本")

if __name__ == "__main__":
    main()