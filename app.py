import re
from flask import Flask, render_template, request, redirect, url_for
from wiki_client import WikiAgent
from services.spotify import SpotifyHandler

app = Flask(__name__)
agent = WikiAgent()

sp_handler = SpotifyHandler(client_id="97d33694cfc244108d9fdf068f419317", client_secret="cd7077144fe54cec9a12fd72d7481c48")

@app.route('/')
def home():
    return render_template('index.html', error=None)

@app.route('/playlist', methods=['POST'])
def load():
    # 1. Recupero il link dal form
    playlist_url = request.form.get('playlist_url', '').strip()
    
    # 2. Estraggo l'ID (o uso un ID finto se il link è vuoto/sbagliato)
    pid = sp_handler.extract_id_from_url(playlist_url)
    
    # 3. Recupero le tracce (reali o demo)
    tracks, is_demo = sp_handler.get_playlist_tracks(pid)

    # 4. Renderizzo la pagina playlist.html passando i dati
    return render_template('playlist.html', tracks=tracks, pid=pid, demo=is_demo)

@app.route('/track')
def track_detail():
    # Recuperiamo i dati passati dal link (senza interrogare API complesse)
    title = request.args.get('title')
    artist = request.args.get('artist')
    album = request.args.get('album')
    
    # Qui renderizziamo la pagina intermedia
    return render_template('track.html', title=title, artist=artist, album=album)

@app.route('/artist/<name>')
def artist_detail(name):
    data = agent.get_artist_data(name)
    if data and 'coords' in data:
        try:
            coords_raw = data['coords']['value'].replace("Point(", "").replace(")", "").split(" ")
            data['lat'] = coords_raw[1]
            data['lng'] = coords_raw[0]
        except Exception as e:
            print(f"Errore coordinate: {e}")
    return render_template('artist.html', artist=name, data=data)

if __name__ == '__main__':
    print("Avvio del server di Integrazione Applicativa...")
    app.run(host='127.0.0.1', port=5000, debug=True)