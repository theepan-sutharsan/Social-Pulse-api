"""
Social Pulse API — YouTube Video & Audio Downloader Service
Extracts metadata, validates video duration/status, and downloads audio via yt-dlp.
"""
import os
import re
import tempfile
import yt_dlp


class VideoDownloadError(Exception):
    """Exception raised when YouTube video processing or download fails."""
    pass


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    if not url:
        return ""
    
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"youtube\.com\/embed\/([0-9A-Za-z_-]{11})",
        r"youtube\.com\/shorts\/([0-9A-Za-z_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""


def _get_ffmpeg_executable() -> str | None:
    """Resolve ffmpeg binary path from imageio-ffmpeg if not in system PATH."""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    return None


def get_video_metadata(url: str) -> dict:
    """
    Extract video metadata without downloading.
    Validates availability and maximum duration (30 mins / 1800s).
    """
    clean_url = url.strip()
    if not clean_url:
        raise VideoDownloadError("YouTube URL is required.")

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)
            
            if not info:
                raise VideoDownloadError("Unable to fetch video information.")
                
            duration = info.get('duration') or 0
            if duration > 1800:
                raise VideoDownloadError("Video duration exceeds 30 minutes limit for analysis.")
                
            video_id = info.get('id') or extract_video_id(clean_url)
            thumbnail_url = (
                info.get('thumbnail') or
                f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            )

            return {
                "id": video_id,
                "title": info.get('title') or "Untitled Video",
                "duration": duration,
                "thumbnail_url": thumbnail_url,
                "uploader": info.get('uploader') or "Unknown Channel",
                "view_count": info.get('view_count') or 0,
            }
    except yt_dlp.utils.DownloadError as e:
        err_msg = str(e)
        if "Private video" in err_msg or "Video unavailable" in err_msg:
            raise VideoDownloadError("This video is private, unavailable, or deleted.")
        raise VideoDownloadError(f"Failed to process YouTube URL: {err_msg}")
    except Exception as e:
        if isinstance(e, VideoDownloadError):
            raise
        raise VideoDownloadError(f"Error fetching video details: {str(e)}")


def download_youtube_audio(url: str, output_dir: str = None) -> tuple[str, dict]:
    """
    Downloads audio from YouTube video using yt-dlp.
    Automatically configures imageio-ffmpeg executable to avoid missing ffmpeg errors.
    Returns tuple of (audio_file_path, metadata_dict).
    """
    metadata = get_video_metadata(url)
    
    if not output_dir:
        output_dir = tempfile.mkdtemp(prefix="sp_yt_audio_")
    os.makedirs(output_dir, exist_ok=True)

    output_template = os.path.join(output_dir, f"{metadata['id']}.%(ext)s")
    ffmpeg_exe = _get_ffmpeg_executable()

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
    }

    if ffmpeg_exe:
        ydl_opts['ffmpeg_location'] = ffmpeg_exe
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url.strip()])
            
        expected_audio = os.path.join(output_dir, f"{metadata['id']}.mp3")
        if not os.path.exists(expected_audio):
            # Check for raw audio files (.m4a, .webm, .opus, etc.) if conversion was skipped
            files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith(metadata['id'])]
            if files:
                expected_audio = files[0]
            else:
                raise VideoDownloadError("Downloaded audio file could not be found.")
                
        return expected_audio, metadata
    except yt_dlp.utils.DownloadError as e:
        # Fallback retry without postprocessor if ffmpeg conversion fails
        if 'ffmpeg_location' in ydl_opts:
            try:
                del ydl_opts['ffmpeg_location']
                del ydl_opts['postprocessors']
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url.strip()])
                files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith(metadata['id'])]
                if files:
                    return files[0], metadata
            except Exception:
                pass
        raise VideoDownloadError(f"Failed to download audio: {str(e)}")
    except Exception as e:
        if isinstance(e, VideoDownloadError):
            raise
        raise VideoDownloadError(f"Audio extraction error: {str(e)}")
