from http.server import (ThreadingHTTPServer)
from . import __version__
from .api import (DashboardHandler)
from .config import (COMMANDS_DIR, HOST, PORT)

def main():
    print("")
    print(f"TabletControl {__version__}")
    print("----------------")
    print(f"Listening on {HOST}:{PORT}")
    print(f"Commands: {COMMANDS_DIR}")
    print("")

    server = ThreadingHTTPServer((HOST, PORT), DashboardHandler)

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nStopping TabletControl.")

    finally:
        server.server_close()

if __name__ == "__main__":
    main()