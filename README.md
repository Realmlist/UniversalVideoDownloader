# Universal Video Downloader

A simple Flask web application to download videos or audio (MP4/MP3) from YouTube, Vimeo, Twitter, TikTok, and 1000+ sites using yt-dlp and FFmpeg.

## Features
- Download videos as MP4 or extract audio as MP3
- Simple, modern web UI (Tailwind CSS)
- Rate limiting to prevent abuse
- Temporary file cleanup
- Docker support for easy deployment

## Requirements
- Python 3.11+
- FFmpeg (installed in Docker image)

## Quick Start (Docker)

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd VideoDownloader
   ```
2. **Build and run the Docker container:**
   ```bash
   docker build -t video-downloader .
   docker run -p 5000:5000 --env-file .env video-downloader
   ```
3. **Open in your browser:**
   - Go to [http://localhost:5000](http://localhost:5000)

## Configuration

You can set environment variables in a `.env` file:

```
FLASK_SECRET_KEY=<your-secret-key-here>
RATE_LIMIT_DEFAULT="50 per minute"
RATE_LIMIT_START_DOWNLOAD="15 per minute"
RATE_LIMIT_API_DOWNLOAD="20 per minute"
HOST="0.0.0.0"
PORT="5000"
FLASK_ENV=production
FLASK_DEBUG="false"
```

## Usage
- Enter a video URL and select MP4 (video) or MP3 (audio).
- Click **Download**. The file will be prepared and downloaded automatically.
- Temporary files are deleted after download or after 1 hour.

## Development
- Install dependencies: `pip install -r requirements.txt`
- Run locally: `python app.py`
- The app will be available at [http://localhost:5000](http://localhost:5000)

## Notes
- Only MP4 and MP3 formats are supported.
- All downloads are processed securely and deleted after transfer.
- Some sites may restrict downloading of their content.
- **Generated with DeepSeek because I'm lazy and don't intend to use this in a professional nor production setting.**

## License
MIT
