#!/usr/bin/env python3
"""VJ Audio Analysis Server - API + Static Files"""
import os, sys, json, tempfile, subprocess, cgi
from http.server import HTTPServer, BaseHTTPRequestHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_DIR = os.path.join(BASE_DIR)
WEB_DIR = os.path.dirname(os.path.abspath(__file__))

CTYPES = {
    'html': 'text/html; charset=utf-8',
    'js': 'application/javascript',
    'css': 'text/css',
    'json': 'application/json',
    'png': 'image/png',
    'ico': 'image/x-icon',
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        routes = {
            '/': '/timeline.html',
            '/index.html': '/index.html',
            '/full.html': '/full.html',
            '/segments.html': '/segments.html',
            '/timeline.html': '/timeline.html',
        }
        path = routes.get(self.path, self.path)
        self.serve_static(path)

    def do_POST(self):
        apis = {
            '/api/beats': self.api_beats,
            '/api/segments': self.api_segments,
            '/api/key': self.api_key,
            '/api/energy': self.api_energy,
            '/api/emotion': self.api_emotion,
            '/api/full': self.api_full,
            '/api/visual_map': self.api_visual_map,
        }
        fn = apis.get(self.path)
        if fn:
            fn()
        else:
            self.send_error(404, 'Not Found')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def serve_static(self, path):
        filename = WEB_DIR + path
        if not os.path.exists(filename):
            self.send_error(404, f'Not found: {path}')
            return
        ext = path.rsplit('.', 1)[-1] if '.' in path else 'html'
        ctype = CTYPES.get(ext, 'text/plain; charset=utf-8')
        with open(filename, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def parse_audio(self):
        try:
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' in content_type:
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={'REQUEST_METHOD': 'POST'}
                )
                file_item = form['audio']
                if not file_item.filename:
                    return None
                suffix = os.path.splitext(file_item.filename)[1] or '.wav'
            else:
                data = self.rfile.read()
                suffix = '.wav'
                file_item = data
        except Exception:
            return None

        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        if hasattr(file_item, 'file'):
            tmp.write(file_item.file.read())
        else:
            tmp.write(file_item)
        tmp.close()
        return tmp.name

    def run_analysis(self, func_name, path, **kwargs):
        args_str = ', '.join(f'{k}={repr(v)}' for k, v in kwargs.items())
        code = (
            f"import sys, json; "
            f"sys.path.insert(0, {repr(MODULE_DIR)}); "
            f"import audio_analysis_module as am; "
            f"r = am.{func_name}({repr(path)}{',' + args_str if args_str else ''}); "
            f"print(json.dumps(r, ensure_ascii=False))"
        )
        try:
            proc = subprocess.run(
                ['python3', '-c', code],
                capture_output=True, timeout=60, text=True
            )
            if proc.returncode != 0:
                return {'success': False, 'error': proc.stderr[:300]}
            return json.loads(proc.stdout)
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': '分析超时（60秒）'}
        except Exception as e:
            return {'success': False, 'error': str(e)[:200]}

    def _handle(self, func_name, **extra):
        path = self.parse_audio()
        if not path:
            self.send_json({'success': False, 'error': 'No audio file'})
            return
        try:
            result = self.run_analysis(func_name, path, **extra)
            self.send_json({'success': True, 'data': result})
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass

    def api_beats(self):
        self._handle('analyze_beats')

    def api_segments(self):
        # Parse k from query string or POST body (without consuming rfile prematurely)
        k = 6
        if '?' in self.path:
            try:
                qs = self.path.split('?')[1]
                for pair in qs.split('&'):
                    if pair.startswith('k='):
                        k = int(pair.split('=')[1])
                        break
            except Exception:
                pass
        self._handle('analyze_segments', k=k)

    def api_key(self):
        self._handle('analyze_key')

    def api_energy(self):
        self._handle('analyze_energy')

    def api_emotion(self):
        self._handle('analyze_emotion')

    def api_full(self):
        self._handle('full_analysis')

    def api_visual_map(self):
        path = self.parse_audio()
        if not path:
            self.send_json({'success': False, 'error': 'No audio file'})
            return
        try:
            # 1. 音频分析
            audio_result = self.run_analysis('full_analysis', path)
            if not isinstance(audio_result, dict) or 'error' in audio_result:
                self.send_json({'success': False, 'error': str(audio_result.get('error', 'Analysis failed'))})
                return

            data = audio_result
            bpm = data.get('beat', {}).get('bpm', 120.0)
            beat_positions = data.get('beat', {}).get('beats', [])
            dur = data.get('beat', {}).get('dur', 30.0)
            segs_raw = data.get('seg', {}).get('segs', [])
            n_segs = len(segs_raw)

            # 2. 格式转换
            beats = []
            for i, pos in enumerate(beat_positions):
                is_accent = (i % 4 == 0)
                strength = 1.0 if is_accent else (0.6 if i % 2 == 0 else 0.3)
                beats.append({'start': float(pos), 'strength': strength, 'is_accent': is_accent})

            sections = []
            for i, s in enumerate(segs_raw):
                ratio = i / (n_segs - 1) if n_segs > 1 else 0.5
                if ratio < 0.15: sec_type = 'intro'
                elif ratio < 0.35: sec_type = 'verse'
                elif ratio < 0.55: sec_type = 'chorus'
                elif ratio < 0.75: sec_type = 'bridge'
                else: sec_type = 'outro'
                sec_beats = [b for b in beats if s['s'] <= b['start'] < s['e']]
                sec_energy = sum(b['strength'] for b in sec_beats) / len(sec_beats) if sec_beats else 0.5
                sections.append({'start': s['s'], 'end': s['e'], 'type': sec_type, 'energy': sec_energy})

            energy_data = data.get('ener', data.get('energy', {}))
            avg_energy = energy_data.get('avg_rms', 0.5) if isinstance(energy_data, dict) else 0.5
            energy_curve = [{'timestamp': 0.0, 'energy': avg_energy}, {'timestamp': dur / 2, 'energy': min(1.0, avg_energy * 1.3)}, {'timestamp': dur, 'energy': avg_energy * 0.8}]

            audio_formatted = {'bpm': bpm, 'duration': dur, 'beats': beats, 'sections': sections, 'energy_curve': energy_curve}

            # 3. 调用 vj_timeline_mapper
            code = (
                f"import sys, json; "
                f"sys.path.insert(0, {repr(os.path.join(MODULE_DIR, 'src', 'pipelines'))}); "
                f"from vj_timeline_mapper import map_audio_to_visual, generate_visual_timeline, PALETTES; "
                f"af = json.loads({repr(json.dumps(audio_formatted))}); "
                f"vis = map_audio_to_visual(af); "
                f"tl = generate_visual_timeline(af, fps=30); "
                f"out = {{"
                f"  'bpm': vis['bpm'], 'total_beats': vis['total_beats'], 'total_segments': vis['total_segments'], "
                f"  'global': vis['global'].to_dict(), "
                f"  'beats': [b.to_dict() for b in vis['beats']], "
                f"  'segments': [{{'start': s.start, 'end': s.end, 'section_type': s.section_type, 'bpm': s.bpm, 'energy': s.energy, 'params': s.params.to_dict()}} for s in vis['segments']], "
                f"  'timeline': tl, 'palettes': PALETTES"
                f"}}; "
                f"print(json.dumps(out, ensure_ascii=False))"
            )
            proc = subprocess.run(['python3', '-c', code], capture_output=True, timeout=30, text=True)
            if proc.returncode != 0:
                self.send_json({'success': False, 'error': proc.stderr[:500]})
            else:
                self.send_json({'success': True, **json.loads(proc.stdout)})
        except Exception as e:
            self.send_json({'success': False, 'error': str(e)[:300]})
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}", flush=True)


def run(port=9123):
    print(f"""
🎵 VJ Audio Analysis Server
   本地:   http://localhost:{port}/full.html
   API端点:
     POST /api/beats       — 节拍检测
     POST /api/segments    — 段落划分
     POST /api/key         — 调性检测
     POST /api/energy      — 能量分析
     POST /api/emotion     — 情绪分析
     POST /api/full        — 完整分析
     POST /api/visual_map  — 视觉映射
""", flush=True)
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()


if __name__ == '__main__':
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 9123)
