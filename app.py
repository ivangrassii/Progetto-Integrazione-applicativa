import re
from flask import Flask, render_template, request, redirect, url_for
from services.wiki_client import WikiAgent
from services.spotify import SpotifyHandler

app = Flask(__name__)
agent = WikiAgent()

sp_handler = SpotifyHandler(client_id="97d33694cfc244108d9fdf068f419317", client_secret="cd7077144fe54cec9a12fd72d7481c48")

@app.route('/')
def home():
    return render_template('index.html', error=None)

@app.route('/playlist', methods=['POST'])
def load():
    playlist_url = request.form.get('playlist_url', '').strip()
    pid = sp_handler.extract_id_from_url(playlist_url)
    tracks, is_demo = sp_handler.get_playlist_tracks(pid)
    return render_template('playlist.html', tracks=tracks, pid=pid, demo=is_demo)

@app.route('/track')
def track_detail():
    title = request.args.get('title', 'Sconosciuto')
    artist = request.args.get('artist', 'Sconosciuto')
    album = request.args.get('album', 'Sconosciuto')
    spotify_image = request.args.get('image')
    
    track_url = agent.get_track_url(title, artist)
    
    if track_url:
        wiki_data = agent.get_track_details(track_url)
    else:
        wiki_data = {'found': False, 'artisti_list': [{'name': artist, 'url': None}]}

    # Magia immagine Spotify
    if spotify_image:
        wiki_data['image'] = spotify_image
    elif not wiki_data.get('image'):
        wiki_data['image'] = 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?q=80&w=500&auto=format&fit=crop'

    return render_template('track.html', title=title, artist=artist, album=album, wiki=wiki_data)

# (La rotta /artist la teniamo per la mappa, ma non la usiamo più nei bottoni della traccia)
@app.route('/artist/<name>')
def artist_detail(name):
    # ... [Codice invariato] ...
    pass 

if __name__ == '__main__':
    print("Avvio del server di Integrazione Applicativa...")
    app.run(host='127.0.0.1', port=5001, debug=True)