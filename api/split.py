# api/split.py
from flask import Flask, request, jsonify
import json
import sys
import os

app = Flask(__name__)

@app.route('/api/split', methods=['POST', 'OPTIONS'])
def split_pdf():
    print("=== FLASK API CALLED ===")
    
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
        
    try:
        print("Headers:", dict(request.headers))
        print("Content Type:", request.content_type)
        
        # Get JSON data
        data = request.get_json()
        print("Received data:", data)
        
        response_data = {
            "status": "success",
            "message": "Flask API is working!",
            "received": {
                "url": data.get('url', '')[:50] + '...' if data.get('url') else None,
                "toc_length": len(data.get('toc', '')),
                "source": data.get('source')
            }
        }
        
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        print("Error:", str(e))
        import traceback
        print("Traceback:", traceback.format_exc())
        
        response = jsonify({
            "status": "error", 
            "message": str(e)
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 500
        return response

# Vercel requires this
def handler(request):
    print("Vercel handler called")
    return app(request)