#!/bin/bash
# test_viz_integration.sh - 本体可视化集成测试
set -e

WORKSPACE="/Users/lwj04/.openclaw/workspace-extractor/.worktrees/viz-improvement"
cd "$WORKSPACE"

echo "🧪 本体可视化集成测试"
echo "====================="

# T1: 单元测试
echo ""
echo "📋 T1: standalone generator tests"
python3 -m pytest scripts/test_generate_standalone_viz.py -v 2>&1 | tail -8

# T2: 同步管道测试
echo ""
echo "📋 T2: sync pipeline tests"
python3 -m pytest scripts/test_sync_viz_pipeline.py -v 2>&1 | tail -8

# T3: 生成 standalone HTML
echo ""
echo "📋 T3: generate standalone HTML"
python3 scripts/sync_viz_pipeline.py \
    --ontology data/material_ontology_enhanced.json \
    --nvl-output /tmp/test_nvl.json \
    --html-output /tmp/test_standalone.html 2>&1

# T4: 验证 standalone HTML
echo ""
echo "📋 T4: validate standalone HTML"
SIZE=$(stat -f%z /tmp/test_standalone.html)
echo "  Size: $SIZE bytes"
grep -q 'd3js\.org/d3\|cdn\.jsdelivr\.net/d3\|unpkg\.com/d3\|registry\.npmmirror\.com/d3' /tmp/test_standalone.html && echo "  ❌ FAIL: contains external D3 CDN" || echo "  ✅ No external D3 CDN"
grep -q "NVL_DATA" /tmp/test_standalone.html && echo "  ✅ Data inlined" || echo "  ❌ FAIL: data not inlined"
grep -q "<!DOCTYPE" /tmp/test_standalone.html && echo "  ✅ Valid HTML" || echo "  ❌ FAIL: not valid HTML"
[ "$SIZE" -gt 500000 ] && echo "  ✅ Size OK" || echo "  ❌ FAIL: too small ($SIZE)"

# T5: 检查功能
echo ""
echo "📋 T5: feature checks"
grep -q "loading\|spinner\|spin" /tmp/test_standalone.html && echo "  ✅ Loading UX present" || echo "  ⚠️ No loading UX"
grep -q "fuzzyMatch\|Fuse\|fuse" /tmp/test_standalone.html && echo "  ✅ Fuzzy search present" || echo "  ⚠️ No fuzzy search"

# T6: 启动 HTTP 服务验证
echo ""
echo "📋 T6: HTTP service test"
python3 -m http.server 9998 --directory /tmp &
SERVER_PID=$!
sleep 1
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9998/test_standalone.html)
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null
[ "$HTTP_CODE" = "200" ] && echo "  ✅ HTTP $HTTP_CODE" || echo "  ❌ FAIL: HTTP $HTTP_CODE"

# Cleanup
rm -f /tmp/test_nvl.json /tmp/test_standalone.html

echo ""
echo "====================="
echo "✅ 集成测试完成"
