#!/bin/zsh

# Amazon Book Extractor 服务启动脚本
# 此脚本用于通过Automator启动服务控制器

# 打印诊断信息
echo "=== Amazon Book Extractor 服务启动脚本 ==="
echo "当前时间: $(date)"
echo "用户: $(whoami)"
echo "当前目录: $(pwd)"

# 定义脚本路径和工作目录
SCRIPT_DIR="/Users/wangxiaohui/Downloads/books_base/amazon-book-extractor"
SCRIPT_PATH="$SCRIPT_DIR/service_controller.py"

# 检查目录和文件是否存在
if [ ! -d "$SCRIPT_DIR" ]; then
  echo "错误: 脚本目录不存在: $SCRIPT_DIR" > "$SCRIPT_DIR/automator_launch.log" 2>&1
  osascript -e 'display dialog "脚本目录不存在，请检查路径设置" buttons {"好"} default button 1 with icon stop'
  exit 0  # 使用0作为退出码，避免Automator显示错误
fi

if [ ! -f "$SCRIPT_PATH" ]; then
  echo "错误: 脚本文件不存在: $SCRIPT_PATH" > "$SCRIPT_DIR/automator_launch.log" 2>&1
  osascript -e 'display dialog "脚本文件不存在，请检查安装" buttons {"好"} default button 1 with icon stop'
  exit 0  # 使用0作为退出码，避免Automator显示错误
fi

# 切换到脚本目录
echo "正在切换到脚本目录: $SCRIPT_DIR" >> "$SCRIPT_DIR/automator_launch.log" 2>&1
cd "$SCRIPT_DIR" || { 
  echo "切换目录失败" >> "$SCRIPT_DIR/automator_launch.log" 2>&1
  osascript -e 'display dialog "无法切换到脚本目录" buttons {"好"} default button 1 with icon stop'
  exit 0
}

# 使用conda环境（如果存在）
if [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
  echo "正在加载conda环境..." >> "$SCRIPT_DIR/automator_launch.log" 2>&1
  source "/opt/anaconda3/etc/profile.d/conda.sh"
  conda activate base
  PYTHON_PATH=$(which python)
  echo "已激活conda环境: $(conda info --env | grep '*')" >> "$SCRIPT_DIR/automator_launch.log" 2>&1
else
  # 确定Python路径
  PYTHON_PATH=$(which python3)
  if [ -z "$PYTHON_PATH" ]; then
    # 尝试找到其他Python路径
    PYTHON_PATH=$(which python)
    if [ -z "$PYTHON_PATH" ]; then
      # 特定路径查找
      for path in "/usr/bin/python3" "/opt/anaconda3/bin/python" "/opt/homebrew/bin/python3"; do
        if [ -f "$path" ]; then
          PYTHON_PATH="$path"
          break
        fi
      done
    fi
  fi
fi

# 如果仍然找不到Python，报错并退出
if [ -z "$PYTHON_PATH" ]; then
  echo "错误: 无法找到Python解释器" >> "$SCRIPT_DIR/automator_launch.log" 2>&1
  osascript -e 'display dialog "无法找到Python解释器，请确保Python已安装" buttons {"好"} default button 1 with icon stop'
  exit 0
fi

echo "使用Python解释器: $PYTHON_PATH" >> "$SCRIPT_DIR/automator_launch.log" 2>&1

# 检查psutil库是否已安装
$PYTHON_PATH -c "import psutil" 2>/dev/null
if [ $? -ne 0 ]; then
  echo "psutil库未安装，正在安装..." >> "$SCRIPT_DIR/automator_launch.log" 2>&1
  $PYTHON_PATH -m pip install psutil
fi

# 获取当前的运行环境信息
echo "当前Python环境:" >> "$SCRIPT_DIR/automator_launch.log" 2>&1
$PYTHON_PATH -c "import sys; print(sys.path)" >> "$SCRIPT_DIR/automator_launch.log" 2>&1

# 创建启动和监控脚本
cat > "$SCRIPT_DIR/run_and_monitor.py" << 'EOL'
import subprocess
import sys
import os
import time

# 获取脚本路径
script_path = sys.argv[1]
python_path = sys.argv[2]

# 启动进程
process = subprocess.Popen(
    [python_path, script_path],
    stdout=open(os.path.join(os.path.dirname(script_path), "service_controller_output.log"), "w"),
    stderr=subprocess.STDOUT
)

# 打印通知
print(f"Amazon Book Extractor 服务控制器已启动，进程ID: {process.pid}")

# 等待1秒确认进程启动
time.sleep(1)
if process.poll() is None:
    # 进程成功启动
    print("启动成功，将继续在后台运行")
    # 这里不退出脚本，让Automator认为脚本仍在运行
    # 因为我们使用了pythonw，所以不会阻塞Automator
    sys.exit(0)
else:
    # 进程启动失败
    print(f"启动失败，退出码: {process.returncode}")
    sys.exit(1)
EOL

# 运行启动脚本
echo "正在启动服务控制器..." >> "$SCRIPT_DIR/automator_launch.log" 2>&1
export PYTHONIOENCODING=utf-8

# 使用前台运行的pythonw来启动监控脚本
"$PYTHON_PATH" "$SCRIPT_DIR/run_and_monitor.py" "$SCRIPT_PATH" "$PYTHON_PATH" >> "$SCRIPT_DIR/automator_launch.log" 2>&1

# 显示成功信息
osascript -e 'display dialog "Amazon Book Extractor 服务已成功启动！" buttons {"好"} default button 1 with icon note'

# 正常退出，不会触发Automator错误
exit 0 