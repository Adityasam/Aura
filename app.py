from flask import Flask, request, Response, render_template, jsonify, render_template_string, send_file, send_from_directory
import requests
from flask_cors import CORS
from bs4 import BeautifulSoup as BS
from ytmusicapi import YTMusic
from pytubefix import YouTube
import os

app = Flask(__name__)
CORS(app)
ytmusic = YTMusic()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('.', 'service-worker.js')

@app.route('/search', methods=['GET'])
def proxy():
    search = ytmusic.search(request.args.get('search'))

    #for song in search:
    song_info = []

    for song in search:
        videoId = song.get("videoId")
        category = song.get("category")
        artist = song.get("artists", [])
        resultType = song.get("resultType", "").lower()
        
        artists = []
        for art in artist:
            artists.append(art.get("name", ""))
        song_name = song.get("title", "")
        thumbnail = song.get("thumbnails", [])
        if len(thumbnail) > 0:
            thumbnail = thumbnail[0].get("url")

        if song_name != "":
            song_info.append({
                "song_name": song_name,
                "artist_name": ", ".join(artists),
                "image": thumbnail,
                "id": videoId,
                "category": category,
                "resultType": resultType
            })

    # Return as JSON
    return jsonify({
        "url": "",
        "link_count": 0,
        "links": [],
        "song_list": song_info
    })

@app.route("/load_song", methods=['GET'])
def load_song():
    songid = request.args.get("id")
    url = "https://www.youtube.com/watch?v=" + songid
    yt = YouTube(url)

    name = songid+".m4a"
    ys = yt.streams.get_audio_only()

    ys.download(output_path="songs", filename = name)
    
    AUDIO_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "songs")
    path = os.path.join(AUDIO_FOLDER, name)

    # Return file with correct MIME type
    return send_file(path, mimetype="audio/mp4", as_attachment=False)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
