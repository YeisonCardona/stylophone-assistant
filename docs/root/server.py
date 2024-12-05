from http.server import SimpleHTTPRequestHandler, HTTPServer
import os

class CustomHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Modifica la ruta para servir desde "/stylophone-assistant"
        base_path = os.path.abspath("docs")
        
        # Asegúrate de que todo esté dentro de "/stylophone-assistant"
        if not path.startswith("/stylophone-assistant"):
            self.send_error(404, "File not found")
            return ""
        
        # Remueve "/stylophone-assistant" de la ruta
        path = path[len("/stylophone-assistant"):]
        return os.path.join(base_path, path.lstrip("/"))

if __name__ == "__main__":
    PORT = 8002
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, CustomHandler)
    print(f"Serving on http://localhost:{PORT}/stylophone-assistant")
    httpd.serve_forever()

