import http.server
import socketserver
import json
import os
import urllib.parse
import db_helper

PORT = 8502
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class DashboardHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Initialize with current directory as root to serve static files
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/api/candidates":
            # API endpoint to fetch candidate list
            try:
                # Query parameters parsing (optional, client-side handles role selection anyway)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                role_filter = query_params.get("role", ["All"])[0]

                # Fetch records from db_helper
                candidates = db_helper.get_candidates(role_filter)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                
                # Write JSON payload
                self.wfile.write(json.dumps(candidates).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                
        elif path == "/" or path == "/index.html" or path == "/dashboard":
            # Serve the dashboard.html file
            dashboard_file_path = os.path.join(DIRECTORY, "dashboard.html")
            if os.path.exists(dashboard_file_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                with open(dashboard_file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "dashboard.html file not found")
        else:
            # Fall back to standard static file serving (for favicon, styles, etc.)
            super().do_GET()

def run_server():
    # Ensure database is initialized before serving
    db_helper.init_db()
    
    # Allow port reuse to avoid address already in use errors on rapid restarts
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), DashboardHTTPRequestHandler) as httpd:
        print(f"==================================================")
        print(f" HR Dashboard Server successfully started on port {PORT}")
        print(f" Access URL: http://localhost:{PORT}")
        print(f"==================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down HR Dashboard Server...")

if __name__ == "__main__":
    run_server()
