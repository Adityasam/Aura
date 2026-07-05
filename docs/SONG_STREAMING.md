# Song Streaming System

Chunked, progressive audio streaming for the player. Playback starts on the first ~10s of audio instead of waiting for the whole file to download and transcode.

## Why

The original `/load_song` downloads the full audio via yt-dlp, transcodes, then returns the entire file. For long songs the user waits for the whole download before hearing anything. The streaming path pipes audio out as it is produced, so playback begins in ~2–3s.

## Architecture

```
YouTube ──> yt-dlp (bestaudio) ──> ffmpeg (transcode to fMP4) ──> Flask chunked HTTP
                                                                        │
                                                                        ▼
                          Browser: fetch ReadableStream ──> MediaSource / SourceBuffer ──> <audio>
                                                                        │
                                                                        ▼ (on stream end)
                                                          one Blob ──> IndexedDB (offline cache)
```

## Server — `/load_song_stream` (app.py)

`GET /load_song_stream?id=<youtubeId>&type=song`

- **Cache hit:** if `songs/<id>.m4a` exists, streams the file bytes directly (65 KB reads).
- **Cache miss:** spawns two piped subprocesses:
  1. `yt-dlp -f bestaudio/best -o -` → writes source audio to stdout.
     - `bestaudio/best` (not bare `bestaudio`) is required — bare `bestaudio` fails on YouTube's SABR-only sessions.
  2. `ffmpeg` reads that on stdin, transcodes to **fragmented MP4 (AAC)** on stdout.
- The generator reads ffmpeg stdout in 64 KB blocks, `yield`s each block (Flask chunked transfer), and **tees** the same bytes to `songs/<id>.m4a.part`.
- On clean finish (`ffmpeg returncode == 0`, non-empty file) the part file is atomically `os.replace`d to `songs/<id>.m4a`. On any failure/abort the part file is deleted — no corrupt cache.
- Response mimetype: `audio/mp4`, no `Content-Length` → chunked.

### ffmpeg flags

```
-analyzeduration 0 -probesize 65536    # start decoding immediately, don't buffer input to probe
-i pipe:0
-vn -c:a aac -b:a 128k                 # audio only, transcode to AAC 128k
-f mp4
-movflags frag_keyframe+empty_moov+default_base_moof   # fragmented MP4 (init segment first, then fragments)
-frag_duration 10000000                # 10s fragments (value is MICROSECONDS)
pipe:1
```

- **fMP4 is mandatory.** Plain m4a/mp4 has its `moov` atom at the end, so the browser cannot decode partial bytes. `empty_moov` emits the init segment first, then self-contained `moof`/`mdat` fragments the browser can decode as they arrive.
- `-analyzeduration 0 -probesize 65536` cut time-to-first-byte from ~4.6s to ~2.3s. The remaining ~2s is yt-dlp extraction, largely unavoidable.
- `-frag_duration` is in **microseconds**: `10000000` = 10 seconds.

The output is saved as `.m4a`; it is valid fMP4/AAC and plays fine on replay via a normal blob `src`, and is compatible with the old `/load_song` cache check.

## Client — `streamSong()` (templates/index.html)

Chosen only when: `type === "song"`, `window.MediaSource` exists, and `MediaSource.isTypeSupported('audio/mp4; codecs="mp4a.40.2"')`. Otherwise falls back to `legacyLoad()` (whole-file fetch → blob).

Flow:
1. Create `MediaSource`, set `player.src = URL.createObjectURL(ms)`.
2. On `sourceopen`, add a `SourceBuffer` for `audio/mp4; codecs="mp4a.40.2"`.
3. `fetch('/load_song_stream?...')`, read `res.body.getReader()` loop.
4. Each chunk is pushed to an **append queue** and to a `chunks[]` array.
   - A `SourceBuffer` can only append one buffer at a time, so `pump()` appends the next only when `!sb.updating`; the `updateend` event drives the next append.
   - Fetch read chunks do **not** align with fMP4 fragment boundaries — that's fine, MSE buffers and parses the byte stream in order.
5. On the **first** chunk, `player.play()` is called → playback starts.
6. On stream end: `ms.endOfStream()`, then `new Blob(chunks, {type:'audio/mp4'})` → **one** `saveBlob()` → **one** IndexedDB record (key = song id).

### Single-file save

All fragments are concatenated client-side into one Blob and written once. Chunks are only separate in-flight; there is never per-chunk IndexedDB writing, and the cache holds one record per song.

## Duration handling

MSE reports `player.duration === Infinity` until `endOfStream()`. Handled by:

- Search results carry `duration` (seconds) + `duration_text` (`m:ss`); `format_duration()` in app.py.
- On click, `total_time` is set immediately from `song.duration`, and `currentSongDuration` is stored.
- `effectiveDuration()` returns finite `player.duration` when known, else `currentSongDuration`.
- `formatTime()` clamps non-finite/negative → `0` (prevents `Infinity:NaN`).
- `total_time` only refreshes to `player.duration` when it is finite (`loadedmetadata` / `durationchange`).

## Seeking while streaming

Chunks arrive sequentially from the start, so only the downloaded portion is seekable.

- `seekToPercent(percent)` computes target from `effectiveDuration()`.
- While still streaming (`player.duration` is `Infinity`): forward seeks are **clamped to `bufferedEnd() - 0.3s`** — can't jump into un-downloaded audio. Backward seeks are always allowed.
- Once finalized (finite duration): seek anywhere.
- Progress bar uses `effectiveDuration()` so it advances during the stream (previously stuck at 0% because of division by `Infinity`).

## Fallbacks

- MSE unsupported / non-`song` type → `legacyLoad()` (old whole-file path).
- Stream `fetch` fails or `!res.ok` → `endOfStream()` then `legacyLoad()`.
- Old `/load_song` endpoint is untouched and still used for video and as fallback.

## Requirements / environment

- ffmpeg at `C:\ffmpeg\bin\ffmpeg.exe` (`FFMPEG_BIN` in app.py).
- yt-dlp invoked as `python -m yt_dlp` (uses the running interpreter).
- Downloaded/streamed files cached in `songs/`.

## Known limitations

- Forward-seek limited to downloaded portion (inherent to sequential progressive streaming).
- AAC transcode costs CPU per active stream.
- yt-dlp extraction (~2s) dominates start latency and is hard to reduce further.
- Offline/saved songs only show duration after being (re)saved from a search result that carried it.
