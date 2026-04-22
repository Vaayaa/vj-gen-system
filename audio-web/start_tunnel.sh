#!/bin/bash
# 启动公网Tunnel (Serveo.net)
# 使用方式: ./start_tunnel.sh

echo "启动 Serveo.net 公网隧道..."
echo "本地服务需先运行: python app.py --port 5001"

# 使用nohup后台运行
nohup ssh -T \
    -o StrictHostKeyChecking=no \
    -o ServerAliveInterval=30 \
    -R 80:localhost:5001 \
    serveo.net > /tmp/serveo_audio.log 2>&1 &

SERVEO_PID=$!
echo "Serveo PID: $SERVEO_PID"

# 等待URL生成
sleep 8

if [ -f /tmp/serveo_audio.log ]; then
    URL=$(grep -o 'https://[^ ]*serveousercontent.com' /tmp/serveo_audio.log | head -1)
    if [ -n "$URL" ]; then
        echo ""
        echo "============================================"
        echo "公网访问地址: $URL"
        echo "============================================"
        echo "备用方式 (cloudflared):"
        echo "  cloudflared tunnel --url http://localhost:5001 --protocol http2"
        echo ""
    else
        echo "等待URL生成中..."
        tail -f /tmp/serveo_audio.log | while read line; do
            echo "$line"
            if echo "$line" | grep -q 'serveousercontent.com'; then
                echo "$line" | grep -o 'https://[^ ]*serveousercontent.com'
                pkill -f "tail -f /tmp/serveo_audio.log"
            fi
        done
    fi
fi

echo ""
echo "Tunnel日志: /tmp/serveo_audio.log"
echo "停止Tunnel: kill $SERVEO_PID"
