import re
from flask import Flask, render_template, request, redirect, url_for
from wiki_client import WikiAgent
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

app = Flask(__name__)
agent = WikiAgent()

# --- CONFIGURAZIONE SPOTIFY API ---
SPOTIPY_CLIENT_ID = 'INSERISCI_QUI_IL_TUO_CLIENT_ID'
SPOTIPY_CLIENT_SECRET = 'INSERISCI_QUI_IL_TUO_CLIENT_SECRET'

try:
    auth_manager = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)
    sp = spotipy.Spotify(auth_manager=auth_manager)
except Exception:
    sp = None

@app.route('/')
def home():
    return render_template('index.html', error=None)

@app.route('/load-playlist', methods=['POST'])
def load():
    playlist_url = request.form.get('playlist_url', '').strip()
    
    # 1. VALIDAZIONE DEL LINK (Se fallisce -> Torna alla Home con Errore)
    spotify_pattern = re.compile(r"^https?://open\.spotify\.com/playlist/([a-zA-Z0-9]+)")
    match = spotify_pattern.match(playlist_url)
    
    if not match:
        return render_template('index.html', error="Errore: Il link inserito non è valido. Formato richiesto: https://open.spotify.com/playlist/...")

    playlist_id = match.group(1)
    current_playlist = []

    # 2. CHIAMATA REALE ALLE API DI SPOTIFY
    try:
        if not sp:
            raise Exception("Credenziali Spotify non configurate.")
            
        results = sp.playlist_items(playlist_id)
        
        for item in results.get('items', []):
            track = item.get('track')
            if track:
                current_playlist.append({
                    "title": track['name'],
                    "artist": track['artists'][0]['name'],
                    "album": track['album']['name']
                })
                
        # SUCCESSO: Mostriamo la playlist reale
        return render_template('playlist.html', playlist=current_playlist, playlist_id=playlist_id, trial_mode=False)

    except Exception as e:
        # 3. FALLIMENTO API -> MODALITÀ DI PROVA (Nessun redirect alla pagina nera!)
        print(f"API Fallita, avvio Modalità di Prova: {e}")
        
        trial_playlist = [
            {"title": "Move (Modalità di Prova)", "artist": "Adam Port", "album": "Move"},
            {"title": "FINCHÉ NON ARRIVA LA BELLA VITA", "artist": "Artie 5ive", "album": "FINCHÉ NON ARRIVA..."},
            {"title": "No Me Conoce - Remix", "artist": "Jhayco", "album": "FAMOUZ"}
        ]
        
        return render_template('playlist.html', playlist=trial_playlist, playlist_id=playlist_id, trial_mode=True)

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