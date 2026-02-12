import re
from flask import Flask, render_template, request, redirect, url_for
from services.wiki_client import WikiAgent
from services.spotify import SpotifyHandler

app = Flask(__name__)
agent = WikiAgent()

sp_handler = SpotifyHandler(client_id="aa75bf8321234d9493c0e84adfe3d20e", client_secret="b3c8ac21c6f944e7975d33275678ab3c")

@app.route('/')
def home():
    return render_template('index.html', error=None)

@app.route('/playlist', methods=['POST'])
def load():
    playlist_url = request.form.get('playlist_url', '').strip()
    pid = sp_handler.extract_id_from_url(playlist_url)
    tracks, is_demo = sp_handler.get_playlist_tracks(pid)
    return render_template('playlist.html', tracks=tracks, pid=pid, demo=is_demo)

@app.route('/resolve_track')
def resolve_track():
    title = request.args.get('title')
    artist = request.args.get('artist')
    album = request.args.get('album', '')
    img = request.args.get('image', '')
    track_url, artist_url = agent.get_track_url(title, artist)

    if track_url:

        return redirect(url_for('track_detail', 
                              id=track_url, 
                              artist_id=artist_url,
                              title=title, 
                              artist=artist, 
                              album=album, 
                              image=img))
    else:
        return redirect(url_for('track_detail', 
                              found='false',
                              title=title, 
                              artist=artist, 
                              album=album, 
                              image=img))

@app.route('/track')
def track_detail():
    wikidata_id = request.args.get('id')
    wikidata_artist_id = request.args.get('artist_id') 

    title = request.args.get('title', 'Sconosciuto')
    artist = request.args.get('artist', 'Sconosciuto')
    album = request.args.get('album', '')
    spotify_image = request.args.get('image', '')
    
    wiki_data = {
        'found': False, 
        'artisti_list': [{'name': artist, 'url': None}],
        'recommendations': [] 
    }

    if wikidata_id:
  
        details = agent.get_track_details(wikidata_id)
        
        if details['found']:
            wiki_data = details 
            recs = agent.get_recommendations(wikidata_id, wikidata_artist_id)
            wiki_data['recommendations'] = recs

    if spotify_image:
        wiki_data['image'] = spotify_image
    elif not wiki_data.get('image'):
        wiki_data['image'] = 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?q=80&w=500'

    return render_template('track.html', title=title, artist=artist, album=album, wiki=wiki_data)


@app.route('/artista')
def artist_detail():
    artist_url = request.args.get('url')
    
    if not artist_url:
        return "URL Artista mancante", 400
        
    # Chiamata al nuovo metodo del WikiAgent
    artist_data = agent.get_artist_details(artist_url)
    
    if not artist_data['found']:
        return "Artista non trovato su Wikidata", 404
        
    return render_template('artista.html', artist=artist_data)

if __name__ == '__main__':
    print("Avvio del server di Integrazione Applicativa...")
    app.run(host='127.0.0.1', port=5001, debug=True)