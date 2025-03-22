#!/bin/bash
# 监控local_service.log文件，检查是否有导入TheBrain的日志

echo "监控本地服务日志，查找TheBrain导入相关记录..."
echo "按Ctrl+C终止监控"
echo

cd /Users/wangxiaohui/Downloads/books_base/amazon-book-extractor

# 监控当前日志内容
tail -f local_service.log | grep -i "brain\|brain\|import"