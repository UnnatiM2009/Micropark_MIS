"""
Start the dashboard and open it in the browser.

    python run_demo.py

Meant for showing the dashboard on a laptop. It picks a free port, starts the
server, waits until it is actually answering, then opens the browser. It also
prints an address that works from a phone on the same wi-fi, which is useful
when you want to hand the phone across the table.

Press Ctrl+C in this window to stop.
"""

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

PREFERRED_PORTS = [8000, 8001, 8080, 8600, 9000]


def find_port():
    for port in PREFERRED_PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    # nothing free in the list, let the system choose
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", 0))
        return s.getsockname()[1]


def lan_ip():
    """Best guess at this machine's address on the office network."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.4)
            s.connect(("8.8.8.8", 80))  # no packet is actually sent
            return s.getsockname()[0]
    except OSError:
        return None


def banner(port, ip, source):
    line = "=" * 62
    print("\n" + line)
    print("  MICROPARK LOGISTICS - PHARMA OPERATIONS MIS")
    print(line)
    print(f"  On this laptop : http://127.0.0.1:{port}")
    if ip:
        print(f"  On the wi-fi   : http://{ip}:{port}")
        print("                   (open this on a phone on the same network)")
    print(f"  Data source    : {source}")
    print(line)
    print("  Press Ctrl+C here to stop the dashboard.")
    print(line + "\n")


def main():
    try:
        import uvicorn
        from app.main import app
        from app import store
    except ImportError as exc:
        print("\nSomething is not installed yet:", exc)
        print("Run this first:  pip install -r requirements.txt\n")
        sys.exit(1)

    store.load()  # read the data before the browser opens, so the first screen is instant

    port = find_port()
    ip = lan_ip()
    url = f"http://127.0.0.1:{port}"

    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # wait until the server is genuinely answering before opening the browser
    for _ in range(100):
        if getattr(server, "started", False):
            break
        time.sleep(0.1)
    else:
        print("The server did not start. Check the messages above.")
        sys.exit(1)

    banner(port, ip, store.source())

    if os.getenv("NO_BROWSER") != "1":
        webbrowser.open(url)

    try:
        while thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping the dashboard. You can close this window.")
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
