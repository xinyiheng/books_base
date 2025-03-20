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
