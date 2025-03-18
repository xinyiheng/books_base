#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import signal
import subprocess
import time
import psutil

SERVICE_NAME = "local_service.py"
LOG_FILE = "service.log"

def get_service_pid():
    """获取运行中的服务进程ID"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and SERVICE_NAME in ' '.join(cmdline):
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def start_service():
    """启动服务"""
    pid = get_service_pid()
    if pid:
        print(f"服务已经在运行中 (PID: {pid})")
        return
    
    print("正在启动服务...")
    log_file = open(LOG_FILE, 'a')
    subprocess.Popen(
        ["python", SERVICE_NAME], 
        stdout=log_file,
        stderr=log_file,
        start_new_session=True
    )
    
    # 等待服务启动
    for _ in range(5):
        time.sleep(1)
        pid = get_service_pid()
        if pid:
            print(f"服务已成功启动 (PID: {pid})")
            break
    else:
        print("服务可能未正常启动，请检查日志文件")

def stop_service():
    """停止服务"""
    pid = get_service_pid()
    if not pid:
        print("服务未运行")
        return
    
    print(f"正在停止服务 (PID: {pid})...")
    try:
        # 尝试优雅地终止进程
        os.kill(pid, signal.SIGTERM)
        
        # 等待进程结束
        for _ in range(5):
            time.sleep(1)
            if not psutil.pid_exists(pid):
                print("服务已停止")
                return
        
        # 如果进程仍在运行，强制终止
        print("服务未响应，强制终止中...")
        os.kill(pid, signal.SIGKILL)
        print("服务已强制停止")
    except Exception as e:
        print(f"停止服务时出错: {e}")

def restart_service():
    """重启服务"""
    stop_service()
    time.sleep(2)
    start_service()

def show_status():
    """显示服务状态"""
    pid = get_service_pid()
    if pid:
        print(f"服务正在运行 (PID: {pid})")
    else:
        print("服务未运行")

def print_usage():
    """打印使用说明"""
    print(f"使用方法: python {os.path.basename(__file__)} [start|stop|restart|status]")
    print("  start   - 启动服务")
    print("  stop    - 停止服务")
    print("  restart - 重启服务")
    print("  status  - 显示服务状态")

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ["start", "stop", "restart", "status"]:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "start":
        start_service()
    elif command == "stop":
        stop_service()
    elif command == "restart":
        restart_service()
    elif command == "status":
        show_status()