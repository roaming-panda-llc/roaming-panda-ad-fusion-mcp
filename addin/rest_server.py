"""
Simple REST server for Fusion 360 MCP integration.
Runs inside Fusion's embedded Python environment.

THREADING NOTE: Fusion 360's API is NOT thread-safe. All API calls must happen
on the main UI thread. This server uses a request queue and CustomEvent to
marshal API calls to the main thread.
"""

import json
import threading
import queue
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote

# Will be set by FusionMCP.py
fusion_api = None
fire_custom_event_func = None

# Threading synchronization for main thread execution
request_queue = queue.Queue()
responses = {}  # request_id -> (event, result)
responses_lock = threading.Lock()

# Timeout for waiting on main thread execution (seconds)
MAIN_THREAD_TIMEOUT = 300  # 5 minutes for complex operations


def execute_on_main_thread(func_name, *args):
    """Queue a request and wait for main thread to execute it.

    This is called from the HTTP handler thread. It puts a request in the queue,
    fires a CustomEvent to wake up the main thread, and waits for the result.
    """
    if not fire_custom_event_func:
        return {"error": "Custom event not initialized"}

    request_id = str(uuid.uuid4())
    event = threading.Event()

    with responses_lock:
        responses[request_id] = (event, None)

    # Put request in queue
    request_queue.put((request_id, func_name, args))

    # Fire custom event to wake up main thread
    try:
        fire_custom_event_func()
    except Exception as e:
        with responses_lock:
            responses.pop(request_id, None)
        return {"error": f"Failed to fire custom event: {str(e)}"}

    # Wait for result with timeout
    event.wait(timeout=MAIN_THREAD_TIMEOUT)

    with responses_lock:
        result_tuple = responses.pop(request_id, (None, None))

    _, result = result_tuple
    if result is None:
        return {"error": "Timeout waiting for main thread execution"}

    return result


def process_queue_on_main_thread():
    """Process all queued requests on the main thread.

    This is called by the CustomEvent handler in FusionMCP.py.
    It runs on Fusion's main UI thread where API calls are safe.
    """
    while not request_queue.empty():
        try:
            request_id, func_name, func_args = request_queue.get_nowait()
        except queue.Empty:
            break

        # Execute the actual Fusion API call
        try:
            if fusion_api and hasattr(fusion_api, func_name):
                func = getattr(fusion_api, func_name)
                result = func(*func_args)
            else:
                result = {"error": f"Unknown function: {func_name}"}
        except Exception as e:
            result = {"error": f"API call failed: {str(e)}"}

        # Store result and signal waiting thread
        with responses_lock:
            if request_id in responses:
                event, _ = responses[request_id]
                responses[request_id] = (event, result)
                event.set()


class FusionRESTHandler(BaseHTTPRequestHandler):
    """Handle REST requests from MCP bridge."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def send_json(self, data, status=200):
        """Send JSON response."""
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_image(self, image_bytes):
        """Send PNG image response."""
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(image_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(image_bytes)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            # Health check doesn't need Fusion API
            if path == "/health":
                self.send_json({"status": "ok", "fusion": "connected"})

            elif path == "/document":
                result = execute_on_main_thread("get_document_info")
                status = 500 if "error" in result else 200
                self.send_json(result, status)

            elif path == "/components":
                result = execute_on_main_thread("get_component_tree")
                status = 500 if "error" in result else 200
                self.send_json(result, status)

            elif path == "/sketches":
                result = execute_on_main_thread("get_sketch_info")
                status = 500 if "error" in result else 200
                self.send_json(result, status)

            elif path.startswith("/sketches/"):
                name = unquote(path[10:])  # Remove "/sketches/"
                result = execute_on_main_thread("get_sketch_info", name)
                status = 500 if "error" in result else 200
                self.send_json(result, status)

            elif path == "/bodies":
                result = execute_on_main_thread("get_body_info")
                status = 500 if "error" in result else 200
                self.send_json(result, status)

            elif path.startswith("/bodies/"):
                name = unquote(path[8:])  # Remove "/bodies/"
                result = execute_on_main_thread("get_body_info", name)
                status = 500 if "error" in result else 200
                self.send_json(result, status)

            elif path == "/parameters":
                result = execute_on_main_thread("get_parameters")
                status = 500 if "error" in result else 200
                self.send_json(result, status)

            elif path == "/screenshot":
                result = execute_on_main_thread("export_screenshot")
                if "error" in result:
                    self.send_json(result, 500)
                elif "data_base64" in result:
                    # Decode base64 and send raw PNG
                    import base64
                    image_bytes = base64.b64decode(result["data_base64"])
                    self.send_image(image_bytes)
                else:
                    self.send_json({"error": "No screenshot data"}, 500)

            elif path == "/versions":
                result = execute_on_main_thread("list_versions")
                status = 500 if "error" in result else 200
                self.send_json(result, status)

            else:
                self.send_json({"error": f"Unknown endpoint: {path}"}, 404)

        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def do_POST(self):
        """Handle POST requests for write operations."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = json.loads(self.rfile.read(content_length).decode('utf-8')) if content_length > 0 else {}
        except (ValueError, json.JSONDecodeError) as e:
            self.send_json({"error": f"Invalid JSON: {str(e)}"}, 400)
            return

        path = self.path.split('?')[0]  # Remove query params

        try:
            if path == "/run_script":
                result = execute_on_main_thread("run_script", post_data.get("code", ""))

            elif path == "/sketch/create":
                result = execute_on_main_thread("create_sketch",
                    post_data.get("component_name"),
                    post_data.get("plane"))

            elif path == "/sketch/circle":
                result = execute_on_main_thread("draw_circle",
                    post_data.get("sketch_name"),
                    post_data.get("center_x", 0),
                    post_data.get("center_y", 0),
                    post_data.get("radius", 1))

            elif path == "/extrude":
                result = execute_on_main_thread("extrude",
                    post_data.get("sketch_name"),
                    post_data.get("profile_index", 0),
                    post_data.get("distance", 1),
                    post_data.get("operation", "new"))

            elif path == "/sketch/rectangle":
                result = execute_on_main_thread("draw_rectangle",
                    post_data.get("sketch_name"),
                    post_data.get("x1", 0),
                    post_data.get("y1", 0),
                    post_data.get("x2", 1),
                    post_data.get("y2", 1))

            elif path == "/component/activate":
                result = execute_on_main_thread("activate_component",
                    post_data.get("name"))

            elif path == "/visibility":
                result = execute_on_main_thread("set_visibility",
                    post_data.get("component_name"),
                    post_data.get("visible", True))

            elif path == "/version/restore":
                result = execute_on_main_thread("restore_version",
                    post_data.get("version_number"))

            else:
                self.send_json({"error": f"Unknown POST endpoint: {path}"}, 404)
                return

            status = 500 if "error" in result else 200
            self.send_json(result, status)

        except Exception as e:
            self.send_json({"error": str(e)}, 500)


class RESTServer:
    """REST server that runs in a background thread."""

    def __init__(self, port=3001):
        self.port = port
        self.server = None
        self.thread = None

    def start(self, api_module, custom_event_fire_func):
        """Start the REST server.

        Args:
            api_module: The fusion_api module with API functions
            custom_event_fire_func: Function to fire the CustomEvent
        """
        global fusion_api, fire_custom_event_func
        fusion_api = api_module
        fire_custom_event_func = custom_event_fire_func

        try:
            self.server = HTTPServer(("127.0.0.1", self.port), FusionRESTHandler)
            self.thread = threading.Thread(
                target=self.server.serve_forever, daemon=True
            )
            self.thread.start()
            return True
        except Exception:
            return False

    def stop(self):
        """Stop the REST server."""
        global fire_custom_event_func
        fire_custom_event_func = None

        if self.server:
            self.server.shutdown()
            self.server = None
        self.thread = None
