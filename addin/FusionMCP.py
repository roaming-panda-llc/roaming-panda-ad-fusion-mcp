"""FusionMCP Add-In - Exposes Fusion 360 data via REST API for MCP bridge.

THREADING: Fusion 360's API is NOT thread-safe. All API calls must happen on
the main UI thread. This add-in uses a CustomEvent to marshal API calls from
the REST server's background thread to the main thread.
"""

import adsk.core
import adsk.fusion
import traceback
import sys
import os

# Add the add-in directory to the path for imports
ADDIN_DIR = os.path.dirname(os.path.realpath(__file__))
if ADDIN_DIR not in sys.path:
    sys.path.insert(0, ADDIN_DIR)

import fusion_api
from rest_server import RESTServer, process_queue_on_main_thread

# Global variables
app = None
ui = None
server = None
custom_event = None
custom_event_handler = None

REST_PORT = 3001
CUSTOM_EVENT_ID = "FusionMCPProcessQueue"


class ProcessQueueEventHandler(adsk.core.CustomEventHandler):
    """Handler for the custom event that processes queued requests.

    This handler runs on Fusion's main UI thread, making it safe to call
    the Fusion 360 API from here.
    """

    def __init__(self):
        super().__init__()

    def notify(self, args):
        """Called when the custom event is fired."""
        try:
            # Process all queued requests on the main thread
            process_queue_on_main_thread()
        except Exception:
            # Log errors but don't crash Fusion
            if ui:
                ui.palettes.itemById("TextCommands").writeText(
                    f"FusionMCP error: {traceback.format_exc()}"
                )


def fire_custom_event():
    """Fire the custom event to wake up the main thread.

    This is called from the REST server's background thread.
    """
    if app:
        app.fireCustomEvent(CUSTOM_EVENT_ID, "")


def run(context):
    """Called when the add-in is run."""
    global app, ui, server, custom_event, custom_event_handler

    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Register custom event for thread marshaling
        custom_event = app.registerCustomEvent(CUSTOM_EVENT_ID)
        custom_event_handler = ProcessQueueEventHandler()
        custom_event.add(custom_event_handler)

        # Start the REST server with the custom event fire function
        server = RESTServer(port=REST_PORT)
        if server.start(fusion_api, fire_custom_event):
            ui.messageBox(
                f"FusionMCP REST server started on port {REST_PORT}\n\n"
                "Endpoints:\n"
                f"  GET http://127.0.0.1:{REST_PORT}/health\n"
                f"  GET http://127.0.0.1:{REST_PORT}/document\n"
                f"  GET http://127.0.0.1:{REST_PORT}/components\n"
                f"  GET http://127.0.0.1:{REST_PORT}/sketches\n"
                f"  GET http://127.0.0.1:{REST_PORT}/bodies\n"
                f"  GET http://127.0.0.1:{REST_PORT}/parameters\n"
                f"  GET http://127.0.0.1:{REST_PORT}/screenshot"
            )
        else:
            # Clean up custom event on failure
            if custom_event:
                app.unregisterCustomEvent(CUSTOM_EVENT_ID)
                custom_event = None
            ui.messageBox("Failed to start FusionMCP REST server")
            return

    except Exception:
        if ui:
            ui.messageBox(f"Failed to start FusionMCP:\n{traceback.format_exc()}")


def stop(context=None):
    """Called when the add-in is stopped."""
    global server, custom_event, custom_event_handler

    try:
        # Stop the REST server first
        if server:
            server.stop()
            server = None

        # Unregister custom event
        if custom_event:
            if custom_event_handler:
                custom_event.remove(custom_event_handler)
                custom_event_handler = None
            app.unregisterCustomEvent(CUSTOM_EVENT_ID)
            custom_event = None

        if ui:
            ui.messageBox("FusionMCP REST server stopped")

    except Exception:
        if ui:
            ui.messageBox(f"Error stopping FusionMCP:\n{traceback.format_exc()}")
