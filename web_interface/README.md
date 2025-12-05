# AEGIS Web Interface

This is a web interface for the AEGIS agent.

## How to run

1. Go to the project root.
2. Run the startup script:
   ```bash
   ./run_web_interface.sh
   ```
3. Open your browser at `http://localhost:8000`.

## Features

- **Task Input**: Enter your Terms of Reference (TZ).
- **Real-time Progress**: View logs as the agent works.
- **Download**: Download the generated application as a ZIP file.
- **Dark Mode**: Beautiful dark theme with animations.

## Structure

- `server.py`: FastAPI backend.
- `static/`: Frontend files (HTML, CSS, JS).
