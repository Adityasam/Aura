from flask import Flask, request, Response, render_template, jsonify, render_template_string, send_file, send_from_directory
import requests
from flask_cors import CORS
import yt_dlp
import os
import io
import sys
import subprocess

FFMPEG_BIN = os.path.join("C:\\", "ffmpeg", "bin", "ffmpeg.exe")

app = Flask(__name__)
CORS(app)

# Create songs directory if it doesn't exist
SONGS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "songs")
if not os.path.exists(SONGS_FOLDER):
    os.makedirs(SONGS_FOLDER)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('.', 'service-worker.js')

def format_duration(seconds):
    # seconds (int/float) -> "m:ss" or "h:mm:ss"; empty if unknown
    try:
        s = int(float(seconds))
    except (TypeError, ValueError):
        return ""
    if s <= 0:
        return ""
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"

def get_search_results(query, search_type, limit=10):
    # yt-dlp uses 'ytsearch' for YouTube search.
    # For 'song', we search specifically on YouTube Music using its search URL.
    if search_type == 'song':
        # Appending 'official audio' often yields better metadata for songs in flat extraction
        search_url = f"ytsearch{limit}:{query} official audio"
    else:
        search_url = f"ytsearch{limit}:{query}"
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'skip_download': True,
    }

    if search_type == 'song':
        # YouTube Music extraction sometimes needs a specific playlist items limit
        ydl_opts['playlist_items'] = '1-10'

    song_info = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(search_url, download=False)
            
            entries = []
            if 'entries' in search_results:
                entries = search_results['entries']
            elif search_results.get('_type') == 'playlist':
                entries = search_results.get('entries', [])
            
            for entry in entries:
                if not entry: continue
                
                # Title often contains artist in YouTube Music results
                full_title = entry.get("title", "")
                artist = entry.get("uploader", "")
                song_name = full_title

                # yt-dlp metadata for music often puts artist in uploader or creator
                if not artist:
                    artist = entry.get("creator", "Unknown Artist")
                
                # Better thumbnail detection
                thumbnail = entry.get("thumbnail")
                if not thumbnail:
                    thumbnails = entry.get("thumbnails", [])
                    if thumbnails:
                        # Find the highest quality thumbnail
                        thumbnail = thumbnails[-1].get("url", "")
                
                # If thumbnail is still missing, try to construct it from ID
                if not thumbnail and entry.get("id"):
                    thumbnail = f"https://i.ytimg.com/vi/{entry.get('id')}/hqdefault.jpg"

                duration = entry.get("duration")
                song_info.append({
                    "song_name": song_name,
                    "artist_name": artist,
                    "image": thumbnail or "",
                    "id": entry.get("id", ""),
                    "category": search_type,
                    "resultType": search_type,
                    "duration": duration,
                    "duration_text": format_duration(duration)
                })
    except Exception as e:
        print(f"Search error ({search_type}): {str(e)}")
        # Fallback to standard search if music search fails
        if search_type == 'song':
            return get_search_results(f"{query} audio", 'video_as_song')
        song_info = []

    # If this was a fallback, rename resultType back to 'song'
    if search_type == 'video_as_song':
        for s in song_info:
            s['resultType'] = 'song'
            s['category'] = 'song'

    return song_info

@app.route('/get_song_info', methods=['GET'])
def get_song_info():
    songid = request.args.get('id')
    if not songid:
        return jsonify({"error": "No ID provided"}), 400
    
    url = "https://www.youtube.com/watch?v=" + songid
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "song_name": info.get("title", "Unknown Song"),
                "artist_name": info.get("uploader", info.get("creator", "Unknown Artist")),
                "image": info.get("thumbnail", ""),
                "id": songid,
                "resultType": "song"
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/search', methods=['GET'])
def proxy():
    query = request.args.get('search')
    if not query:
        return jsonify({"song_list": []})

    # Fetch 10 songs and 20 videos to allow for deduplication
    songs = get_search_results(query, 'song', limit=10)
    videos = get_search_results(query, 'video', limit=20)

    # Track seen IDs to prevent duplicates
    # We prioritize songs, so we process them first
    seen_ids = set()
    final_songs = []
    final_videos = []

    # Add songs first (up to 10)
    for song in songs:
        if song['id'] not in seen_ids:
            if len(final_songs) < 10:
                final_songs.append(song)
                seen_ids.add(song['id'])

    # Add videos only if the ID hasn't been seen in songs (up to 10)
    for video in videos:
        if video['id'] not in seen_ids:
            if len(final_videos) < 10:
                final_videos.append(video)
                seen_ids.add(video['id'])

    # Combine for the final list
    deduplicated_list = final_songs + final_videos

    return jsonify({
        "url": "",
        "link_count": len(deduplicated_list),
        "links": [],
        "song_list": deduplicated_list
    })

@app.route("/load_song", methods=['GET'])
def load_song():
    songid = request.args.get("id")
    # Get the type from the request, default to 'song' (audio)
    request_type = request.args.get("type", "song")
    
    if not songid:
        return jsonify({"error": "No ID provided"}), 400
        
    url = "https://www.youtube.com/watch?v=" + songid
    
    # Define file extension based on type
    ext = "mp4" if request_type == "video" else "m4a"
    filename = f"{songid}.{ext}"
    filepath = os.path.join(SONGS_FOLDER, filename)

    # If file already exists, return it immediately
    if os.path.exists(filepath):
        mimetype = "video/mp4" if request_type == "video" else "audio/mp4"
        return send_file(filepath, mimetype=mimetype, as_attachment=False)

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best' if request_type == 'video' else 'bestaudio/best',
        'outtmpl': os.path.join(SONGS_FOLDER, f'{songid}.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': f'C:\\ffmpeg\\bin',
    }

    if request_type == 'song':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
        }]
    else:
        # For video, ensure it's in a compatible format like mp4
        ydl_opts['merge_output_format'] = 'mp4'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Check for the expected file
        if os.path.exists(filepath):
            mimetype = "video/mp4" if request_type == "video" else "audio/mp4"
            return send_file(filepath, mimetype=mimetype, as_attachment=False)
        else:
            # Fallback scan
            for f in os.listdir(SONGS_FOLDER):
                if f.startswith(songid) and f.endswith(f".{ext}"):
                    actual_path = os.path.join(SONGS_FOLDER, f)
                    mimetype = "video/mp4" if request_type == "video" else "audio/mp4"
                    return send_file(actual_path, mimetype=mimetype, as_attachment=False)
            
            return jsonify({"error": f"File not found after download. Checked {filepath}"}), 500
            
    except Exception as e:
        print(f"Error downloading {request_type}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/load_song_stream", methods=['GET'])
def load_song_stream():
    songid = request.args.get("id")
    if not songid:
        return jsonify({"error": "No ID provided"}), 400

    url = "https://www.youtube.com/watch?v=" + songid
    # Streamed output is fragmented-MP4 AAC audio, saved as m4a (compatible with /load_song cache)
    filepath = os.path.join(SONGS_FOLDER, f"{songid}.m4a")

    # Already cached -> stream the file bytes directly
    if os.path.exists(filepath):
        def gen_file():
            with open(filepath, "rb") as fh:
                while True:
                    data = fh.read(65536)
                    if not data:
                        break
                    yield data
        return Response(gen_file(), mimetype="audio/mp4")

    tmp_path = filepath + ".part"

    def generate():
        # yt-dlp downloads bestaudio to stdout -> piped into ffmpeg -> fragmented MP4 on stdout
        ytdlp = subprocess.Popen(
            [sys.executable, "-m", "yt_dlp", "-q", "--no-warnings", "-f", "bestaudio/best", "-o", "-", url],
            stdout=subprocess.PIPE,
        )
        ff = subprocess.Popen(
            [
                FFMPEG_BIN, "-hide_banner", "-loglevel", "error",
                "-i", "pipe:0",
                "-vn", "-c:a", "aac", "-b:a", "128k",
                "-f", "mp4",
                "-movflags", "frag_keyframe+empty_moov+default_base_moof",
                "-frag_duration", "10000000",
                "pipe:1",
            ],
            stdin=ytdlp.stdout,
            stdout=subprocess.PIPE,
        )
        ytdlp.stdout.close()  # allow ytdlp to get SIGPIPE if ff exits

        out = open(tmp_path, "wb")
        ok = False
        try:
            while True:
                data = ff.stdout.read(65536)
                if not data:
                    break
                out.write(data)
                yield data
            ff.wait()
            ytdlp.wait()
            ok = (ff.returncode == 0)
        finally:
            out.close()
            for p in (ff, ytdlp):
                if p.poll() is None:
                    p.kill()
            # Only keep the file if the transcode finished cleanly (atomic rename)
            if ok and os.path.getsize(tmp_path) > 0:
                os.replace(tmp_path, filepath)
            elif os.path.exists(tmp_path):
                os.remove(tmp_path)

    return Response(generate(), mimetype="audio/mp4")


if __name__ == '__main__':
    app.run(debug=True, port=5000)
