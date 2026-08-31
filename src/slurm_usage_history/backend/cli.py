"""CLI entry point for slurm-backend command."""

import contextlib
import logging
import sys


def main():
    """Start the FastAPI backend with uvicorn."""
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn not installed. Install with: pip install slurm-dashboard[web]")
        sys.exit(1)

    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Default configuration
    config = {
        "app": "backend.app.main:app",
        "host": "0.0.0.0",
        "port": 8100,
        "log_level": "info",
    }

    # Check for --reload flag in args
    if "--reload" in sys.argv or "--dev" in sys.argv:
        config["reload"] = True
        print("Starting in development mode with auto-reload...")

    # Check for --workers flag
    if "--workers" in sys.argv:
        idx = sys.argv.index("--workers")
        if idx + 1 < len(sys.argv):
            try:
                workers = int(sys.argv[idx + 1])
                print(f"Using {workers} workers (gunicorn mode)")
                print("Note: Use gunicorn directly for production:")
                print(
                    f"  gunicorn backend.app.main:app --workers {workers} "
                    f"--worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8100"
                )
            except ValueError:
                pass

    # Check for --port flag
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            with contextlib.suppress(ValueError):
                config["port"] = int(sys.argv[idx + 1])

    print(f"Starting SLURM Dashboard backend on http://{config['host']}:{config['port']}")
    print("Press CTRL+C to quit")
    print()
    print("Endpoints:")
    print(f"  - Dashboard: http://{config['host']}:{config['port']}/")
    print(f"  - API docs: http://{config['host']}:{config['port']}/docs")
    print(f"  - Health check: http://{config['host']}:{config['port']}/api/dashboard/health")
    print()

    uvicorn.run(**config)


if __name__ == "__main__":
    main()
