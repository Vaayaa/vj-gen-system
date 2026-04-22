"""
Madmom 音频分析公网页面
VJ智能剪辑系统 - 音频节拍检测Web界面
"""

import os
import sys
import tempfile
import shutil
import uuid
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 兼容性修复
import collections
import collections.abc
for attr in ('MutableSequence', 'Iterable', 'Mapping', 'MutableMapping', 'Callable'):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

import numpy as np
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    if not hasattr(np, 'float'):
        np.float = np.float64
    if not hasattr(np, 'int'):
        np.int = np.int64
    if not hasattr(np, 'complex'):
        np.complex = np.complex128
    if not hasattr(np, 'object'):
        np.object = np.object_
    if not hasattr(np, 'bool'):
        np.bool = np.bool_
    if not hasattr(np, 'str'):
        np.str = np.str_

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS

# 导入 Madmom 分析器
from audio_madmom import MadmomAnalyzer, analyze_with_madmom

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp(prefix='madmom_upload_')
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac', 'ogg', 'aac'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """上传并分析音频文件"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file format. Use MP3, WAV, M4A, FLAC, OGG, or AAC'}), 400
    
    # 保存上传文件
    original_filename = file.filename
    unique_id = str(uuid.uuid4())
    ext = original_filename.rsplit('.', 1)[1].lower()
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}.{ext}")
    file.save(temp_path)
    
    try:
        # 执行 Madmom 分析
        result = analyze_with_madmom(temp_path)
        
        # 获取音频时长
        import librosa
        try:
            y, sr = librosa.load(temp_path, sr=22050, mono=True)
            duration = float(len(y)) / sr
        except Exception:
            duration = result.get('duration', 0)
        
        return jsonify({
            'success': True,
            'file_id': unique_id,
            'filename': original_filename,
            'duration': round(duration, 2),
            'tempo': result.get('tempo', 0),
            'downbeats': result.get('downbeats', []),
            'beats': result.get('beats', []),
            'segments': result.get('segments', []),
            'beat_info': result.get('beat_info', []),
            'beats_per_bar': result.get('beats_per_bar', 4),
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': f'Analysis failed: {str(e)}',
            'trace': traceback.format_exc()
        }), 500
    
    finally:
        # 清理临时文件
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

@app.route('/status')
def status():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'version': '1.0.0',
        'madmom_available': True
    })

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Madmom Audio Analysis Web')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind')
    parser.add_argument('--port', type=int, default=5001, help='Port to bind')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    
    args = parser.parse_args()
    
    print(f"""
╔═══════════════════════════════════════════════════╗
║     Madmom 音频分析公网页面                        ║
║     VJ智能剪辑系统 - 节拍检测测试                   ║
╠═══════════════════════════════════════════════════╣
║  本地访问: http://localhost:{args.port}                ║
║  启动调试: {'--debug' if args.debug else ''}                            ║
╚═══════════════════════════════════════════════════╝
    """)
    
    app.run(host=args.host, port=args.port, debug=args.debug)
