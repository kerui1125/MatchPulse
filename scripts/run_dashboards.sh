#!/bin/bash
# 同时运行本地和生产 Dashboard

echo "🚀 Starting MatchPulse Dashboards..."
echo ""

# 检查生产数据库是否存在
if [ ! -f "match_pulse_prod.db" ]; then
    echo "⚠️  Production database not found"
    echo ""
    echo "Initializing production database..."
    echo ""
    
    # 运行初始化脚本
    bash scripts/init_prod_db.sh
    
    if [ ! -f "match_pulse_prod.db" ]; then
        echo ""
        echo "❌ Failed to initialize production database"
        echo ""
        echo "Starting local dashboard only..."
        echo ""
        streamlit run dashboard/MatchPulse.py
        exit 0
    fi
    
    echo ""
fi

echo "📊 Local Dashboard (Development):"
echo "   http://localhost:8501"
echo "   Database: match_pulse.db"
echo ""
echo "🌐 Production Dashboard:"
echo "   http://localhost:8502"
echo "   Database: match_pulse_prod.db"
echo ""
echo "Press Ctrl+C to stop both dashboards"
echo ""

# 启动本地 Dashboard（后台）
streamlit run dashboard/MatchPulse.py --server.port 8501 &
LOCAL_PID=$!

# 等待一下
sleep 2

# 启动生产 Dashboard（前台）
streamlit run dashboard/MatchPulse.py --server.port 8502 -- --db-path match_pulse_prod.db &
PROD_PID=$!

# 等待任意一个进程结束
wait -n

# 清理：杀死两个进程
kill $LOCAL_PID 2>/dev/null
kill $PROD_PID 2>/dev/null

echo ""
echo "✓ Dashboards stopped"
