#!/bin/bash
# 运行所有音频分析方法对比

echo "🎵 VJ-Gen 音频分析 - 全方法对比"
echo "================================"

# Check Python environments
echo ""
echo "📦 环境状态:"
echo "  Python 3.10 (系统): $(which python3)"
echo "  Conda: $(~/miniconda3/bin/conda --version 2>/dev/null || echo '未找到')"

# Start server if not running
if ! curl -s http://localhost:5001/health > /dev/null 2>&1; then
    echo ""
    echo "⚙️  启动Python服务..."
    cd ~/openclaw-media/projects/vj-gen-system/audio-server
    nohup python3 server.py > /tmp/audio-server.log 2>&1 &
    sleep 2
    echo "  服务已启动 (localhost:5001)"
else
    echo ""
    echo "✅ Python服务已运行"
fi

# Check audio file
AUDIO_FILE="${1:-/Users/jiongenjon/Music/Music/Media.localized/Music/Demo/Unknown Album/决无绝Hadrcore.mp3}"

if [ -f "$AUDIO_FILE" ]; then
    echo ""
    echo "🎼 测试文件: $(basename "$AUDIO_FILE")"
    echo ""
    
    # Run comparison
    echo "🔬 运行对比分析..."
    echo ""
    cd ~/openclaw-media/projects/vj-gen-system/audio-analyzer
    
    # Python 3.10 (librosa + Essentia)
    python3 full_compare.py "$AUDIO_FILE"
    
    echo ""
    echo "================================"
    echo "💡 如需madmom结果，运行:"
    echo "   source ~/miniconda3/envs/madmom-env/activate.sh"
    echo "   python3 full_compare.py '$AUDIO_FILE'"
else
    echo ""
    echo "❌ 音频文件不存在: $AUDIO_FILE"
    echo "   请提供音频文件路径作为参数"
fi
