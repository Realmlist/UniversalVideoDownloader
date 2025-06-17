# 🎬 Universal Video Downloader

A simple Flask web application to download videos or audio (MP4/MP3) from YouTube, Vimeo, Twitter, TikTok, and 1000+ sites using yt-dlp and FFmpeg.

## ✨ Features
- 📹 Download videos as MP4 or extract audio as MP3
- 🖥️ Simple, modern web UI (Tailwind CSS)
- 🚦 Rate limiting to prevent abuse
- 🧹 Temporary file cleanup
- 🐳 Docker support for easy deployment

## ⚙️ Requirements
- 🐍 Python 3.11+
- 🎵 FFmpeg (installed in Docker image)

## 🚀 Quick Start (Docker Compose)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Realmlist/UniversalVideoDownloader.git
   cd UniversalVideoDownloader
   ```
2. **Create a `docker-compose.yml` file:**
   ```yaml
   services:
     video-downloader:
       build: .
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
         MAX_FILESIZE_MB: 2000  # Maximum allowed download size in MB (default: 2000)
   ```
   - **MAX_FILESIZE_MB**: Sets the maximum allowed file size (in megabytes) for downloads. If not set, defaults to `2000` (2GB).
   - All other variables control Flask, rate limits, and server settings.

3. **Start the application:**
   ```bash
   docker compose up --build
   ```

4. **Open in your browser:**
   - Go to [http://localhost:5000](http://localhost:5000)

## 📝 Usage
- Enter a video URL and select MP4 (video) or MP3 (audio).
- Click **Download**. The file will be prepared and downloaded automatically.
- 🧹 Temporary files are deleted after download or after 1 hour.

## 🛠️ Development
- Install dependencies: `pip install -r requirements.txt`
- Run locally: `python app.py`
- The app will be available at [http://localhost:5000](http://localhost:5000)

## 📢 Notes
- Only MP4 and MP3 formats are supported.
- All downloads are processed securely and deleted after transfer.
- Some sites may restrict downloading of their content.
- **Generated with DeepSeek because I'm lazy and don't intend to use this in a professional nor production setting.**

## 📄 License
MIT
