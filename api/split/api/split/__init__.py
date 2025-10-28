# api/split/__init__.py
from http.server import BaseHTTPRequestHandler
import json
import sys
import os

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            print("=== API CALLED ===")
            print("Headers:", dict(self.headers))
            print("Content length:", content_length)
            
            # Parse JSON body
            body = json.loads(post_data.decode('utf-8'))
            print("Body received:", body)
            
            # Send success response
            response = {
                "status": "success", 
                "message": "API is working!",
                "data_received": {
                    "url_length": len(body.get('url', '')),
                    "toc_length": len(body.get('toc', '')),
                    "source": body.get('source')
                }
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            print("Error:", str(e))
            import traceback
            print("Traceback:", traceback.format_exc())
            
            error_response = {
                "status": "error",
                "message": str(e)
            }
            
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode('utf-8'))

def main(request):
    print("Main function called")
    return Handler()