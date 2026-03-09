#!/bin/bash
# 下载 GitHub Actions 的生产数据库

echo "📥 Downloading production database from GitHub Actions..."
echo ""

# 检查 GitHub CLI 是否安装
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) not installed"
    echo ""
    echo "Install it:"
    echo "  macOS: brew install gh"
    echo "  Linux: https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
    echo ""
    exit 1
fi

# 检查是否已登录
if ! gh auth status &> /dev/null; then
    echo "❌ Not logged in to GitHub"
    echo ""
    echo "Login with:"
    echo "  gh auth login"
    echo ""
    exit 1
fi

echo "✓ GitHub CLI ready"
echo ""

# 列出最近的 workflow runs
echo "🔍 Finding workflow run with database artifact..."
echo ""

# 获取最近 10 个 runs (包括 completed 和 failure)
# 因为即使 workflow failed，database artifact 也会上传（if: always()）
RUN_IDS=$(gh run list --workflow="scheduled-scan.yml" --limit 10 --json databaseId,conclusion --jq '.[] | select(.conclusion == "success" or .conclusion == "failure") | .databaseId')

if [ -z "$RUN_IDS" ]; then
    echo "❌ No workflow runs found (completed or failed)"
    echo ""
    echo "Run the scheduled-scan workflow first:"
    echo "  GitHub → Actions → Scheduled Job Scan → Run workflow"
    echo ""
    exit 1
fi

echo "  Searching in recent runs (including failed runs)..."
echo ""

# 尝试每个 run，直到找到有 database artifact 的
FOUND=false

for RUN_ID in $RUN_IDS; do
    # 获取 run 的状态
    RUN_INFO=$(gh run view $RUN_ID --json conclusion,displayTitle --jq '{conclusion: .conclusion, title: .displayTitle}')
    CONCLUSION=$(echo "$RUN_INFO" | jq -r '.conclusion')
    
    if [ "$CONCLUSION" = "failure" ]; then
        echo "  Checking run $RUN_ID (⚠️  failed, but may have database)..."
    else
        echo "  Checking run $RUN_ID (✓ success)..."
    fi
    
    # 临时删除本地 match_pulse.db（如果存在）
    if [ -f "match_pulse.db" ]; then
        mv match_pulse.db match_pulse.db.backup
    fi
    
    # 尝试下载这个 run 的 artifact
    if gh run download $RUN_ID --name matchpulse-database 2>/dev/null; then
        echo ""
        echo "✓ Found database in run $RUN_ID"
        
        # 检查文件是否存在
        if [ -f "match_pulse.db" ]; then
            # 删除旧的 prod 数据库
            if [ -f "match_pulse_prod.db" ]; then
                rm match_pulse_prod.db
            fi
            
            # 重命名为 prod
            mv match_pulse.db match_pulse_prod.db
            
            # 恢复本地数据库
            if [ -f "match_pulse.db.backup" ]; then
                mv match_pulse.db.backup match_pulse.db
            fi
            mv match_pulse.db match_pulse_prod.db
            
            # 显示文件信息
            SIZE=$(ls -lh match_pulse_prod.db | awk '{print $5}')
            echo "✓ Saved to match_pulse_prod.db ($SIZE)"
            
            FOUND=true
            break
        else
            echo "  ⚠️  Database file not found after download"
        fi
    fi
done

if [ "$FOUND" = false ]; then
    echo ""
    echo "❌ No workflow run has the database artifact"
    echo ""
    echo "This means:"
    echo "  1. The workflow hasn't completed successfully yet, OR"
    echo "  2. The workflow was run before the database upload step was added"
    echo ""
    echo "Solution:"
    echo "  Run the workflow manually:"
    echo "    GitHub → Actions → Scheduled Job Scan → Run workflow"
    echo "    Set dry_run=true for testing"
    echo ""
    echo "  Wait for it to complete (~5-10 minutes), then run this script again"
    exit 1
fi

echo ""
echo "✅ Production database ready!"
echo ""
echo "Run production dashboard:"
echo "  streamlit run dashboard/MatchPulse.py --server.port 8502 -- --db-path match_pulse_prod.db"
echo ""
echo "Or use the helper script to run both dashboards:"
echo "  bash scripts/run_dashboards.sh"
