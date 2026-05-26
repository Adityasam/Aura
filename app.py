from flask import Flask, request, Response, render_template, jsonify, render_template_string, send_file, send_from_directory
import requests
from flask_cors import CORS
import yt_dlp
import os
import io

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

                song_info.append({
                    "song_name": song_name,
                    "artist_name": artist,
                    "image": thumbnail or "",
                    "id": entry.get("id", ""),
                    "category": search_type,
                    "resultType": search_type
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
 
if __name__ == '__main__':
    app.run(debug=True, port=5000)
