# Aura Music Player

Aura is a modern, lightweight Progressive Web Application (PWA) for streaming music directly from YouTube Music. It offers a clean, ad-free listening experience with offline capabilities.

## Features

- **Search & Stream**: Search for songs, albums, and artists using the YouTube Music API.
- **High-Quality Audio**: Streams audio directly from YouTube sources.
- **PWA Support**: Installable on mobile and desktop devices with offline caching.
- **Responsive Design**: Built with Bootstrap 5 for a seamless experience on any screen size.
- **Custom UI**: Features smooth animations and a dark-themed interface.

## Project Structure

```
c:\AudioPlayer\
├── app.py                # Main Flask application backend
├── service-worker.js     # Service Worker for PWA functionality
├── requirements.txt      # Python dependencies
├── templates/
│   └── index.html        # Main application interface
├── static/
│   ├── css/              # Custom stylesheets (style.css, myToastr.css)
│   ├── js/               # Custom JavaScript (myToastr.js)
│   ├── img/              # Images and icons
│   └── manifest.json     # Web App Manifest for PWA
└── songs/                # Directory where downloaded songs are temporarily stored
```

## Prerequisites

- **Python 3.x**: Ensure Python is installed on your system.
- **Pip**: Python package installer.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd AudioPlayer
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application:**
    ```bash
    python app.py
    ```

4.  **Access the app:**
    Open your browser and navigate to `http://localhost:5000`.

## Usage

1.  **Search**: Use the search bar to find your favorite songs.
2.  **Play**: Click on a song from the search results to start playing.
3.  **Install (PWA)**: Look for the "Install" prompt in your browser address bar to add Aura to your home screen or desktop.

## Technologies Used

- **Backend**: Python, Flask, Flask-CORS
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **APIs**: `ytmusicapi` (YouTube Music), `pytubefix` (YouTube Audio Download)
- **PWA**: Service Workers, Web App Manifest

## License

This project is open-source and available under the MIT License.
