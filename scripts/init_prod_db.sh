#!/bin/bash
# 初始化生产数据库（如果不存在）

echo "🔧 Initializing production database..."
echo ""

# 检查是否已存在
if [ -f "match_pulse_prod.db" ]; then
    echo "✓ Production database already exists"
    SIZE=$(ls -lh match_pulse_prod.db | awk '{print $5}')
    echo "  Size: $SIZE"
    echo ""
    exit 0
fi

# 尝试从 GitHub Actions 下载
echo "📥 Attempting to download from GitHub Actions..."
echo ""

if bash scripts/download_prod_db.sh; then
    echo ""
    echo "✅ Production database downloaded successfully!"
    exit 0
fi

# 如果下载失败，创建空数据库
echo ""
echo "⚠️  Could not download from GitHub Actions"
echo ""
echo "Creating empty production database..."
echo ""

# 使用 Python 创建空数据库
python3 << 'EOF'
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.tools.db import setup_database, DB_PATH

# 临时修改 DB_PATH
import src.tools.db as db_module
original_path = db_module.DB_PATH
db_module.DB_PATH = 'match_pulse_prod.db'

# 创建数据库
setup_database()

# 恢复原路径
db_module.DB_PATH = original_path

print("✓ Empty database created: match_pulse_prod.db")
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Production database initialized!"
    echo ""
    echo "Note: This is an empty database."
    echo "To get real data, run the GitHub Actions workflow:"
    echo "  GitHub → Actions → Scheduled Job Scan → Run workflow"
    echo ""
    echo "Then download it:"
    echo "  bash scripts/download_prod_db.sh"
else
    echo ""
    echo "❌ Failed to create database"
    exit 1
fi
