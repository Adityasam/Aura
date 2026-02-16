from flask import Flask, request, Response, render_template, jsonify
import requests
from flask_cors import CORS
from bs4 import BeautifulSoup as BS

app = Flask(__name__)
CORS(app)

# Forward headers if needed
headers = {
    "User-Agent": "Flask-Proxy/1.0",
    # Add other headers if necessary (e.g. auth tokens)
}

MAIN_URL = "https://pagalnew.com/"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def proxy():
    # The target URL to call (you can make this dynamic)
    target_url = MAIN_URL + "search.php?find=" + request.args.get('search')
    
    # Make the external request
    resp = requests.get(target_url, headers=headers)

    # Return the exact content and content-type
    soup = BS(resp.text, 'html.parser')

    songs = soup.find_all('a')
    song_info = []

    for song in songs:
        href = song.attrs['href']
        if '/songs/' in href:
            info_div = song.find(class_="main_page_category_music_box")
            name = info_div.find("b").get_text(strip=True)
            albumname = info_div.find("span").get_text(strip = True)
            image = info_div.find("img").attrs['src']

            song_info.append({
                "song_name": name,
                "album_name": albumname,
                "image": image,
                "link": href
            })

    links = [a['href'] for a in soup.find_all('a') if 'href' in a.attrs]

    # Return as JSON
    return jsonify({
        "url": target_url,
        "link_count": len(links),
        "links": links,
        "song_list": song_info
    })

@app.route("/load_song", methods=['GET'])
def load_song():
    url = request.args.get('url')
    target_url = MAIN_URL + request.args.get('url')

    resp = requests.get(target_url, headers=headers)

    # Return the exact content and content-type
    soup = BS(resp.text, 'html.parser')

    aud = soup.find('audio')
    aud_src = aud['src']

    newurl = "https://pagalnew.com/" + aud_src

    response = requests.get(newurl, headers=headers)

    # Check for success
    # if response.status_code == 200:
    #     # Write the binary content to a file
    #     with open("song.mp3", "wb") as f:
    #         f.write(response.content)
    #     print("Image saved as downloaded_image.jpg")
    # else:
    #     print("Failed to fetch media:", response.status_code)


    return Response(
        response.content,                    # raw media bytes
        content_type=resp.headers.get('Content-Type'),  # preserve original type
        status=resp.status_code
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
