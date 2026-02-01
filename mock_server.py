from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class SimpleTargetHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {
            "message": "Hello from the Target Server!",
            "path": self.path,
            "status": "Target reached successfully via Proxy"
        }
        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {
            "message": "POST received by Target!",
            "received_data": json.loads(post_data.decode()) if post_data else None,
            "status": "Success"
        }
        self.wfile.write(json.dumps(response).encode())

def run_target(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleTargetHandler)
    print(f"🎯 Target server running on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run_target()
