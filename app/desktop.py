import time
import socket
import threading
import uvicorn
import webview
import ctypes
import logging
import sys

from app.main import app
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.database import DATABASE_PATH

def configure_logging() -> Path:
    log_directory = Path(DATABASE_PATH).parent / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    log_file = log_directory / "t2speech.log"

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )

    handlers = [file_handler]
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler(sys.stderr))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )

    return log_file


def create_server_socket() -> tuple[socket.socket, int]:
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("127.0.0.1", 0))
    server_socket.listen(128)
    port = server_socket.getsockname()[1]
    return server_socket, port

def start_api_server(
    server_socket: socket.socket,
) -> tuple[uvicorn.Server, threading.Thread]:
    server = uvicorn.Server(
    uvicorn.Config(app, log_level="info", log_config=None)
)
    thread = threading.Thread(
        target=server.run,
        kwargs={"sockets": [server_socket]},
        name="t2speech-api",
        daemon=True,
    )
    thread.start()
    return server, thread

def wait_for_api_server(
    server: uvicorn.Server,
    thread: threading.Thread,
    timeout: float = 15.0,
) -> None:
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if server.started:
            return
        if not thread.is_alive():
            raise RuntimeError("T2Speech server stopped while starting.")
        time.sleep(0.1)

    raise TimeoutError("T2Speech server was not ready in time.")

class DesktopOriginMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_origin: str) -> None:
        super().__init__(app)
        self.allowed_origin = allowed_origin

    async def dispatch(self, request: Request, call_next) -> Response:
        origin = request.headers.get("origin")

        if origin is not None and origin != self.allowed_origin:
            return PlainTextResponse("Forbidden", status_code=403)

        return await call_next(request)

def run_desktop() -> None:
    log_file = configure_logging()
    logger = logging.getLogger("t2speech.desktop")
    logger.info("Desktop startup. Log file: %s", log_file)

    runtime_version = get_webview2_runtime_version()
    if runtime_version is None:
        logger.error("WebView2 Runtime is missing.")
        ctypes.windll.user32.MessageBoxW(
            None,
            (
                "T2Speech requires Microsoft Edge WebView2 Runtime.\n\n"
                "Install it from:\n"
                "https://developer.microsoft.com/microsoft-edge/webview2/\n\n"
                "Then start T2Speech again."
            ),
            "T2Speech - WebView2 Runtime required",
            0x10,
        )
        return

    logger.info("WebView2 Runtime detected: %s", runtime_version)

    server_socket, port = create_server_socket()
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1"],
    )
    app.add_middleware(
        DesktopOriginMiddleware,
        allowed_origin=f"http://127.0.0.1:{port}",
    )

    server = None
    thread = None

    try:
        server, thread = start_api_server(server_socket)
        wait_for_api_server(server, thread)
        logger.info("Local API ready at http://127.0.0.1:%s", port)

        webview.create_window(
            "T2Speech",
            f"http://127.0.0.1:{port}",
            width=1200,
            height=800,
            min_size=(900, 600),
        )
        webview.start(gui="edgechromium")
        logger.info("T2Speech window closed.")

    except Exception:
        logger.exception("Desktop application failed.")
        raise

    finally:
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=10)
        server_socket.close()
        logger.info("Desktop server stopped.")

def get_webview2_runtime_version() -> str | None:
    import winreg

    runtime_key = (
        "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    )
    registry_locations = (
        (
            winreg.HKEY_LOCAL_MACHINE,
            rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{runtime_key}",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{runtime_key}",
        ),
        (
            winreg.HKEY_CURRENT_USER,
            rf"Software\Microsoft\EdgeUpdate\Clients\{runtime_key}",
        ),
    )

    for hive, subkey in registry_locations:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                version, _ = winreg.QueryValueEx(key, "pv")
        except FileNotFoundError:
            continue

        if version and version != "0.0.0.0":
            return version

    return None

if __name__ == "__main__":
    run_desktop()