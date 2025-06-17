import os
import uuid
import time
import threading
import logging
import re
import subprocess
import shlex
from datetime import datetime
from flask import Flask, render_template, request, Response, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import yt_dlp
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create temp directory at startup
TEMP_DIR = os.path.join(os.getcwd(), 'temp_downloads')
os.makedirs(TEMP_DIR, exist_ok=True)
logger.info(f"Created temp download directory at: {TEMP_DIR}")

# Rate Limiting Configuration
# -----------------------------------------------------------------
# Get rate limits from environment variables
DEFAULT_LIMIT = os.environ.get('RATE_LIMIT_DEFAULT', "5 per minute")
START_DOWNLOAD_LIMIT = os.environ.get('RATE_LIMIT_START_DOWNLOAD', "3 per minute")
API_DOWNLOAD_LIMIT = os.environ.get('RATE_LIMIT_API_DOWNLOAD', "5 per minute")

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[DEFAULT_LIMIT]
)

logger.info(f"Rate Limiting Configured:")
logger.info(f"  Default: {DEFAULT_LIMIT}")
logger.info(f"  /start_download: {START_DOWNLOAD_LIMIT}")
logger.info(f"  /download_file: {API_DOWNLOAD_LIMIT}")
# -----------------------------------------------------------------

# MIME type mapping
MIME_TYPES = {
    'mp4': 'video/mp4',
    'mp3': 'audio/mpeg',
}

# Supported formats for transcoding
SUPPORTED_FORMATS = {
    'video': ['mp4'],
    'audio': ['mp3']
}

# Download progress tracking
download_status = {}
last_progress = {}
transcoding_status = {}

# --- Security helper: ensure file operations are safe ---
def is_safe_path(path):
    """Check if the given path is within the temp directory to prevent directory traversal attacks."""
    abs_temp = os.path.abspath(TEMP_DIR)
    abs_path = os.path.abspath(path)
    return os.path.commonpath([abs_temp]) == os.path.commonpath([abs_temp, abs_path])

# --- Utility: Remove ANSI color codes from output ---
def strip_ansi_codes(text):
    """Remove ANSI color codes from a string for clean user-facing output."""
    if not isinstance(text, str):
        return text
    return re.sub(r'\x1b\[[0-9;]*m', '', text)

# --- Flask context: inject current time for templates ---
@app.context_processor
def inject_now():
    """Inject the current datetime into Jinja templates as 'now'."""
    return {'now': datetime.now()}

# --- Download progress hook for yt_dlp ---
def download_hook(d, download_id):
    """Track and update download progress for a given download_id."""
    if d['status'] == 'downloading':
        progress = strip_ansi_codes(d.get('_percent_str', '0%'))
        speed = strip_ansi_codes(d.get('_speed_str', '?'))
        eta = strip_ansi_codes(d.get('_eta_str', '?'))
        last_progress[download_id] = {
            'percent': progress,
            'speed': speed,
            'eta': eta,
            'status': 'downloading'
        }
    elif d['status'] == 'finished':
        last_progress[download_id] = {'status': 'processing'}

# --- Format string selection for yt_dlp ---
def get_format_string(format_choice, quality):
    """Return yt_dlp format string for supported formats. Only MP4 and MP3 are allowed."""
    if format_choice == 'mp4':
        # Always get best available MP4 video+audio
        return 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    elif format_choice == 'mp3':
        # Download best audio for MP3 conversion
        return 'bestaudio/best'
    else:
        raise ValueError('Only MP4 and MP3 formats are supported.')

# --- Transcoding utility: MP4 to MP3 (or MP3 copy) ---
def transcode_file(input_path, output_path, target_format):
    """Transcode a file to MP3 using FFmpeg. Only mp4 to mp3 or mp3 to mp3 (copy) allowed."""
    try:
        input_ext = input_path.split('.')[-1].lower()
        output_ext = output_path.split('.')[-1].lower()
        if input_ext in SUPPORTED_FORMATS['video'] and output_ext in SUPPORTED_FORMATS['audio']:
            cmd = f"ffmpeg -i {shlex.quote(input_path)} -vn -c:a libmp3lame -q:a 2 {shlex.quote(output_path)}"
        elif input_ext in SUPPORTED_FORMATS['audio'] and output_ext in SUPPORTED_FORMATS['audio']:
            cmd = f"ffmpeg -i {shlex.quote(input_path)} -c:a copy {shlex.quote(output_path)}"
        else:
            raise ValueError(f"Unsupported conversion from {input_ext} to {output_ext}")
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        stdout = strip_ansi_codes(stdout.decode('utf-8', errors='ignore'))
        stderr = strip_ansi_codes(stderr.decode('utf-8', errors='ignore'))
        if process.returncode != 0:
            error_msg = f"Transcoding failed: {stderr}"
            logger.error(error_msg)
            raise Exception(error_msg)
        logger.info(strip_ansi_codes(f"Successfully transcoded {input_path} to {output_path}"))
        return True
    except Exception as e:
        logger.error(strip_ansi_codes(f"Transcoding error: {str(e)}"))
        raise

# Max file size for downloads (in MB), configurable via environment variable
MAX_FILESIZE_MB = int(os.environ.get('MAX_FILESIZE_MB', '2000'))  # Default 2000MB (2GB)

# --- Main download logic: handles download and optional transcoding ---
def download_video(url, format_choice, quality, download_id):
    """Download a video as MP4 or MP3. Only MP4 and MP3 are supported. Livestreams are blocked."""
    if format_choice not in ['mp4', 'mp3']:
        raise Exception('Only MP4 and MP3 formats are supported.')
    ydl_format = get_format_string('mp4', quality)
    ydl_opts = {
        'format': ydl_format,
        'quiet': False,
        'no_warnings': True,
        'progress_hooks': [lambda d: download_hook(d, download_id)],
        'noplaylist': True,
        'restrictfilenames': True,
        'socket_timeout': 30,
        'retries': 3,
        'max_filesize': MAX_FILESIZE_MB * 1024 * 1024,  # Use env-configured max size
        'concurrent_fragment_downloads': 4,
    }
    original_path = None
    temp_path = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info.get('is_live') or info.get('was_live'):
                raise Exception('Livestreams are not supported. Please provide a non-live video URL.')
            title = info.get('title', 'video')
            if not title.strip():
                title = "video"
            base_filename = secure_filename(title)[:150]
            temp_filename = f"{download_id}_{base_filename}.mp4"
            original_path = os.path.join(TEMP_DIR, temp_filename)
            ydl_opts['outtmpl'] = original_path
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
                download_status[download_id] = 'downloading'
                ydl_download.download([url])
            if not os.path.exists(original_path):
                raise Exception("Download failed: File not created")
            if os.path.getsize(original_path) == 0:
                raise Exception("Download failed: File is empty")
            if format_choice == 'mp3':
                output_filename = f"{download_id}_{base_filename}.mp3"
                temp_path = os.path.join(TEMP_DIR, output_filename)
                transcode_file(original_path, temp_path, 'mp3')
                try:
                    os.remove(original_path)
                except Exception as e:
                    logger.error(strip_ansi_codes(f"Error removing original file: {str(e)}"))
                final_path = temp_path
                final_format = 'mp3'
            else:
                final_path = original_path
                final_format = 'mp4'
                temp_path = None
            download_status[download_id] = {
                'status': 'ready',
                'filename': f"{base_filename}.{final_format}",
                'path': final_path,
                'size': os.path.getsize(final_path),
                'format': final_format
            }
            return final_path, f"{base_filename}.{final_format}"
    except yt_dlp.utils.DownloadError as e:
        error_msg = f"Download error: {strip_ansi_codes(str(e))}"
        logger.error(error_msg)
        download_status[download_id] = f'error: {error_msg}'
        raise Exception(clean_error_message(str(e)))
    except Exception as e:
        logger.error(strip_ansi_codes(f"Unexpected error: {str(e)}"))
        download_status[download_id] = f'error: {strip_ansi_codes(str(e))}'
        for path in [original_path, temp_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass
        raise

# --- Error message sanitizer ---
def clean_error_message(msg):
    """Remove sensitive info and ANSI codes from error messages for safe API responses."""
    msg = strip_ansi_codes(msg)
    patterns = [
        r"File (.*?) already exists",
        r"path: (.*?)$",
        r"Unable to open file: (.*?):"
    ]
    for pattern in patterns:
        msg = re.sub(pattern, "[redacted]", msg)
    return msg

# --- Flask route: Home page ---
@app.route('/', methods=['GET'])
def index():
    """Render the main index page."""
    return render_template('index.html')

# --- Flask route: Start a new download ---
@app.route('/start_download', methods=['POST'])
@limiter.limit(START_DOWNLOAD_LIMIT)
def start_download():
    """API endpoint to start a new download in a background thread."""
    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({'status': 'error', 'message': 'URL is required'}), 400
        
        format_choice = data.get('format', 'mp4')
        quality = data.get('quality', 'best')
        
        # Create unique download ID
        download_id = uuid.uuid4().hex
        
        # Start download in background thread
        def download_task():
            try:
                temp_path, filename = download_video(url, format_choice, quality, download_id)
            except Exception as e:
                logger.error(strip_ansi_codes(f"Download task failed: {str(e)}"))
        
        threading.Thread(target=download_task, daemon=True).start()
        
        return jsonify({'status': 'started', 'download_id': download_id})
            
    except Exception as e:
        logger.error(strip_ansi_codes(f"Unexpected error: {str(e)}"))
        return jsonify({'status': 'error', 'message': strip_ansi_codes(str(e))}), 500

# --- Flask route: Get download status/progress ---
@app.route('/download_status/<download_id>')
def get_download_status(download_id):
    """API endpoint to get the current status or progress of a download."""
    progress = last_progress.get(download_id, {'status': 'starting'})
    status = download_status.get(download_id, 'not found')
    transcode_status = transcoding_status.get(download_id, '')
    
    if isinstance(status, dict) and status.get('status') == 'ready':
        response_data = {
            'status': 'ready',
            'filename': strip_ansi_codes(status['filename']),
            'path': strip_ansi_codes(status['path']),
            'size': status['size'],
            'format': strip_ansi_codes(status['format'])
        }
        if transcode_status:
            response_data['transcode_status'] = strip_ansi_codes(transcode_status)
        return jsonify(response_data)
    elif isinstance(status, str) and status.startswith('error:'):
        return jsonify({'status': 'error', 'message': strip_ansi_codes(status[6:])})
    else:
        response_data = {
            'status': 'progress',
            'progress': strip_ansi_codes(progress.get('percent', '0%')),
            'speed': strip_ansi_codes(progress.get('speed', '?')),
            'eta': strip_ansi_codes(progress.get('eta', '?')),
            'state': strip_ansi_codes(progress.get('status', 'starting'))
        }
        if transcode_status:
            response_data['transcode_status'] = strip_ansi_codes(transcode_status)
        return jsonify(response_data)

# --- Flask route: Download the completed file ---
@app.route('/download_file/<download_id>')
@limiter.limit(API_DOWNLOAD_LIMIT)
def download_file(download_id):
    """API endpoint to stream the completed file to the user and clean up after download."""
    # Check if download exists
    if download_id not in download_status:
        return jsonify({'status': 'error', 'message': 'Invalid download ID'}), 404
    
    status = download_status[download_id]
    # Handle error status (string)
    if isinstance(status, str):
        return jsonify({'status': 'error', 'message': strip_ansi_codes(status[6:] if status.startswith('error:') else status)}), 400
    if not isinstance(status, dict):
        return jsonify({'status': 'error', 'message': 'Invalid download status'}), 400
    if status.get('status') != 'ready':
        return jsonify({'status': 'error', 'message': 'File not ready'}), 400
    
    file_path = status['path']
    filename = status['filename']
    
    # Security check: verify file is in our temp directory
    if not is_safe_path(file_path):
        return jsonify({'status': 'error', 'message': 'Invalid file path'}), 400
    
    # Get mimetype based on extension
    file_ext = filename.split('.')[-1].lower()
    mimetype = MIME_TYPES.get(file_ext, 'application/octet-stream')
    
    # Format file size for UI
    size = status.get('size', 0)
    size_mb = round(size / (1024 * 1024), 1)
    
    def file_generator():
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(4096 * 10):  # 40KB chunks
                    yield chunk
        finally:
            # Clean up after streaming
            try:
                os.remove(file_path)
                logger.info(strip_ansi_codes(f"Cleaned up temp file: {file_path}"))
                # Remove download status
                if download_id in download_status:
                    del download_status[download_id]
                if download_id in transcoding_status:
                    del transcoding_status[download_id]
            except Exception as e:
                logger.error(strip_ansi_codes(f"Error cleaning up temp file: {str(e)}"))
    
    response = Response(
        file_generator(),
        mimetype=mimetype,
        headers={
            'Content-Disposition': f'attachment; filename="{strip_ansi_codes(filename)}"',
            'Content-Length': str(size),
            'X-File-Size': str(size),
            'X-File-Size-MB': str(size_mb)
        }
    )
    return response

# --- Flask route: Cancel a download and clean up ---
@app.route('/cancel_download/<download_id>')
def cancel_download(download_id):
    """API endpoint to cancel a download and remove any associated files/status."""
    if download_id in download_status:
        # Clean up if file exists
        status = download_status[download_id]
        if isinstance(status, dict) and 'path' in status:
            file_path = status['path']
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
        # Remove status
        del download_status[download_id]
        if download_id in last_progress:
            del last_progress[download_id]
        if download_id in transcoding_status:
            del transcoding_status[download_id]
        return jsonify({'status': 'canceled'})
    return jsonify({'status': 'not found'}), 404

# --- Flask error handler: Rate limit exceeded ---
@app.errorhandler(429)
def ratelimit_handler(e):
    """Return a JSON error when the user exceeds the rate limit."""
    return jsonify({
        'status': 'error', 
        'message': strip_ansi_codes('Too many requests. Please try again later.'),
        'limits': {
            'default': strip_ansi_codes(DEFAULT_LIMIT),
            'start_download': strip_ansi_codes(START_DOWNLOAD_LIMIT),
            'download_file': strip_ansi_codes(API_DOWNLOAD_LIMIT)
        }
    }), 429

# --- Background thread: Periodically clean up old temp files ---
def cleanup_temp_folder():
    """Clean up the temp folder every hour, deleting files older than 1 hour."""
    while True:
        try:
            now = time.time()
            logger.info("Starting temp folder cleanup...")
            
            for filename in os.listdir(TEMP_DIR):
                file_path = os.path.join(TEMP_DIR, filename)
                
                # Skip directories
                if not os.path.isfile(file_path):
                    continue
                
                # Get file age in seconds
                file_age = now - os.path.getmtime(file_path)
                
                # Delete files older than 1 hour (3600 seconds)
                if file_age > 3600:
                    try:
                        os.remove(file_path)
                        logger.info(f"Deleted old temp file: {filename}")
                    except Exception as e:
                        logger.error(f"Error deleting temp file {filename}: {str(e)}")
            
            # Sleep for 1 hour
            time.sleep(3600)
            
        except Exception as e:
            logger.error(f"Error in cleanup thread: {str(e)}")
            # Sleep a bit before retrying in case of errors
            time.sleep(60)

# --- App entry point: Start cleanup thread and Flask server ---
if __name__ == '__main__':
    # Start the cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_temp_folder, daemon=True)
    cleanup_thread.start()
    logger.info("Started temp folder cleanup thread")
    
    # Get host and port from environment
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    
    # Check if we're in production mode
    is_production = os.environ.get('FLASK_ENV', 'production') == 'production'
    
    # Run with appropriate server
    if is_production:
        from waitress import serve
        logger.info(f"Starting Waitress server on {host}:{port}")
        serve(app, host=host, port=port)
    else:
        # Run development server
        debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
        logger.info(f"Starting development server on {host}:{port} (Debug: {debug})")
        app.run(host=host, port=port, debug=debug)