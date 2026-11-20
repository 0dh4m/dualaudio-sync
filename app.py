import os
import sys

backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

if __name__ == "__main__":
    import app
    app.app.run(host="0.0.0.0", port=app.SERVER_PORT, threaded=True, debug=False)
