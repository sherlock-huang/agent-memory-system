#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Experience File Server
简单的 HTTP 文件服务器，用于存储和分发经验 MD 文件
"""

import os
import json
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import uuid
from datetime import datetime

# 配置
HOST = "0.0.0.0"
PORT = 8998
BASE_DIR = "./experiences"
AUTH_TOKEN = "agent-memory-token-2026"

# 确保目录存在
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "2026-04"), exist_ok=True)


class ExperienceHandler(BaseHTTPRequestHandler):
    """处理经验文件请求"""
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")
    
    def check_auth(self):
        """检查认证"""
        auth_header = self.headers.get('Authorization', '')
        if auth_header != f"Bearer {AUTH_TOKEN}":
            self.send_error(401, "Unauthorized")
            return False
        return True
    
    def do_GET(self):
        """处理 GET 请求"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # 根路径返回索引
        if path == "/" or path == "/index":
            self.send_index()
        elif path.startswith("/experiences/"):
            self.send_file(path)
        elif path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """处理 POST 请求 - 上传文件"""
        if not self.check_auth():
            return
        
        parsed = urlparse(self.path)
        
        if parsed.path == "/upload":
            self.handle_upload()
        elif parsed.path == "/delete":
            self.handle_delete()
        else:
            self.send_error(404, "Not Found")
    
    def send_index(self):
        """返回文件索引"""
        files = []
        for root, dirs, filenames in os.walk(BASE_DIR):
            for filename in filenames:
                if filename.endswith('.md'):
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, BASE_DIR)
                    stat = os.stat(full_path)
                    files.append({
                        "path": f"/experiences/{rel_path}",
                        "name": filename,
                        "size": stat.st_size,
                        "modified": int(stat.st_mtime * 1000)
                    })
        
        response = {
            "status": "ok",
            "count": len(files),
            "files": files
        }
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
    
    def send_file(self, path):
        """发送文件"""
        # 移除 /experiences/ 前缀
        filename = path[len("/experiences/"):]
        filepath = os.path.join(BASE_DIR, filename)
        
        if not os.path.exists(filepath):
            self.send_error(404, "File Not Found")
            return
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", len(content.encode('utf-8')))
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))
    
    def handle_upload(self):
        """处理文件上传"""
        content_length = int(self.headers.get('Content-Length', 0))
        
        if content_length == 0:
            self.send_error(400, "Empty body")
            return
        
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            # 直接作为文本处理
            content = body.decode('utf-8')
            data = {"content": content}
        
        # 获取文件信息
        content = data.get('content', '')
        code = data.get('code', '')
        filename = data.get('filename', '')
        
        if not code and not filename:
            self.send_error(400, "Missing code or filename")
            return
        
        # 生成文件名
        if not filename:
            filename = f"{code}.md"
        
        # 按年月组织目录
        now = datetime.now()
        date_dir = f"{now.year}-{now.month:02d}"
        target_dir = os.path.join(BASE_DIR, date_dir)
        os.makedirs(target_dir, exist_ok=True)
        
        filepath = os.path.join(target_dir, filename)
        
        # 计算哈希
        file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 返回结果
        response = {
            "status": "uploaded",
            "path": f"/experiences/{date_dir}/{filename}",
            "hash": file_hash,
            "size": len(content.encode('utf-8'))
        }
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
    
    def handle_delete(self):
        """处理文件删除"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body.decode('utf-8'))
        except:
            self.send_error(400, "Invalid JSON")
            return
        
        filepath = data.get('path', '')
        if not filepath:
            self.send_error(400, "Missing path")
            return
        
        # 移除 /experiences/ 前缀
        filename = filepath[len("/experiences/"):]
        fullpath = os.path.join(BASE_DIR, filename)
        
        if os.path.exists(fullpath):
            os.remove(fullpath)
            response = {"status": "deleted", "path": filepath}
        else:
            response = {"status": "not_found", "path": filepath}
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())


def main():
    """启动服务器"""
    server = HTTPServer((HOST, PORT), ExperienceHandler)
    print(f"=" * 50)
    print(f"  Experience File Server")
    print(f"=" * 50)
    print(f"  Host: {HOST}")
    print(f"  Port: {PORT}")
    print(f"  Base: {os.path.abspath(BASE_DIR)}")
    print(f"  Token: {AUTH_TOKEN[:20]}...")
    print(f"=" * 50)
    print()
    print("Endpoints:")
    print("  GET  /                  - List files")
    print("  GET  /experiences/...   - Get file")
    print("  POST /upload            - Upload file")
    print("  POST /delete           - Delete file")
    print("  GET  /health           - Health check")
    print()
    print("Upload example:")
    print(f'  curl -X POST http://localhost:{PORT}/upload \\')
    print(f'    -H "Authorization: Bearer {AUTH_TOKEN}" \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f'    -d \'{{"code": "EXP-BACKEND-FASTAPI-0001", "content": "# Hello"}}\'')
    print()
    
    try:
        print(f"Server started on http://{HOST}:{PORT}")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        server.shutdown()


if __name__ == "__main__":
    main()
