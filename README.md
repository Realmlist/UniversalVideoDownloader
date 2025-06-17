# 🎬 Universal Video Downloader

A simple Flask web application to download videos or audio (MP4/MP3) from YouTube, Vimeo, Twitter, TikTok, and 1000+ sites using [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [FFmpeg](https://ffmpeg.org/).

## ✨ Features
- 📹 Download videos as MP4 or extract audio as MP3
- 🖥️ Simple, modern web UI (Tailwind CSS)
- 🚦 Rate limiting to prevent abuse
- 🧹 Temporary file cleanup
- 🐳 Docker support for easy deployment

![image](https://github.com/user-attachments/assets/a7dc368a-99f3-4868-841d-2b636fc1c511)

## ⚙️ Requirements
- 🐍 Python 3.11+
- 🎵 [FFmpeg](https://ffmpeg.org/) (installed in Docker image)
> ⚠️ **Note:** You must provide your own reverse proxy (such as [Nginx](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/), [Traefik](https://doc.traefik.io/traefik/), [Caddy](https://caddyserver.com/docs/quick-starts/reverse-proxy), and many more) in front of this application to enable HTTPS and other production security features. This app does not handle HTTPS or advanced security by itself.

## 🚀 Quick Start (Docker)

You can use the official Docker image from Docker Hub with Docker Compose for the fastest setup:

```yaml
services:
  universal-video-downloader:
    image: realmlist/universalvideodownloader
    ports:
      - "5000:5000"
    environment:
      FLASK_SECRET_KEY: <your-secret-key-here>
      RATE_LIMIT_DEFAULT: "50 per minute"
      RATE_LIMIT_START_DOWNLOAD: "15 per minute"
      RATE_LIMIT_API_DOWNLOAD: "20 per minute"
      HOST: "0.0.0.0"
      PORT: "5000"
      FLASK_ENV: production
      FLASK_DEBUG: "false"
      MAX_FILESIZE_MB: 2000
```

- **FLASK_SECRET_KEY**: Secret key for Flask session security (required).
- **RATE_LIMIT_DEFAULT**: Default rate limit for all endpoints (e.g., `50 per minute`).
- **RATE_LIMIT_START_DOWNLOAD**: Rate limit for starting downloads (e.g., `15 per minute`).
- **RATE_LIMIT_API_DOWNLOAD**: Rate limit for file download endpoint (e.g., `20 per minute`).
- **HOST**: Host address to bind the server (default: `0.0.0.0`).
- **PORT**: Port to run the server on (default: `5000`).
- **FLASK_ENV**: Set to `production` to run with [Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/), or `development` for Flask's dev server.
- **FLASK_DEBUG**: Set to `true` to enable Flask debug mode (default: `false`).
- **MAX_FILESIZE_MB**: Sets the maximum allowed file size (in megabytes) for downloads. If not set, defaults to `2000` (2GB).

Or, if you prefer to build the image yourself, clone the repository and use `docker run`:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Realmlist/UniversalVideoDownloader.git
   cd UniversalVideoDownloader
   ```
2. **Build and run the image:**
   ```bash
   docker build -t universalvideodownloader .
   docker run -d \
     -e FLASK_SECRET_KEY=<your-secret-key-here> \
     -e RATE_LIMIT_DEFAULT="50 per minute" \
     -e RATE_LIMIT_START_DOWNLOAD="15 per minute" \
     -e RATE_LIMIT_API_DOWNLOAD="20 per minute" \
     -e HOST="0.0.0.0" \
     -e PORT="5000" \
     -e FLASK_ENV=production \
     -e FLASK_DEBUG="false" \
     -e MAX_FILESIZE_MB=2000 \
     -p 5000:5000 \
     universalvideodownloader
   ```

3. **Open in your browser:**
   - Go to [http://localhost:5000](http://localhost:5000)

## 📝 Usage
1. Enter a video URL and select MP4 (video) or MP3 (audio).
2. Click **Download**. The file will be prepared and downloaded automatically.
3. Temporary files are deleted after download or after 1 hour.

## 🛠️ Development
- Install dependencies: `pip install -r requirements.txt`
- Run locally: `python app.py`
- The app will be available at [http://localhost:5000](http://localhost:5000)

## 📢 Notes
- Only MP4 and MP3 formats are supported.
- All downloads are processed securely and deleted after transfer.
- Some sites may restrict downloading of their content.
- **Generated with DeepSeek because I'm lazy and don't intend to use this in a professional nor production setting.**
- **I will provide no support on possible issues. Fork or create pull requests instead.**

## 📄 License
MIT
