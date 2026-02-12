import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re

class SpotifyHandler:
    def __init__(self, client_id, client_secret):
        self.sp = None
        self.active = False
        
        print(f"🔑 [Spotify] Tentativo connessione con ID: {client_id[:4]}***")
        
        if client_id and client_secret:
            try:
                auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
                self.sp = spotipy.Spotify(auth_manager=auth_manager)
                self.sp.search(q='test', limit=1)
                self.active = True
                print("[Spotify] Connessione API riuscita!")
            except Exception as e:
                print(f"[Spotify] Errore Chiavi/Autenticazione: {e}")
                self.active = False
        else:
            print("⚠️ [Spotify] Chiavi mancanti.")

    def extract_id_from_url(self, url):
        if not url: return "demo"
        try:
            clean_url = url.strip().split('?')[0]
            match = re.search(r"playlist[/:](\w{22})", clean_url)
            
            if match:
                found_id = match.group(1)
                print(f"🔎 [Spotify] ID Trovato: {found_id}")
                return found_id
            
            if len(clean_url) == 22 and re.match(r"^\w{22}$", clean_url):
                return clean_url
                
            print(f"⚠️ [Spotify] Link non riconosciuto: {url}")
            return "demo"
        except Exception as e:
            print(f"[Spotify] Errore analisi link: {e}")
            return "demo"

    def get_playlist_tracks(self, playlist_id):
        tracks = []
        
        # 1. TENTATIVO API (Dati Reali)
        if self.active and playlist_id != "demo":
            try:
                print(f"🔄 [Spotify] Scarico playlist: {playlist_id}...")
                
                results = self.sp.playlist_items(playlist_id)
                items = results.get('items', [])
                
                while results['next']:
                    results = self.sp.next(results)
                    items.extend(results['items'])
                
                for item in items:
                    track = item.get('track')
                    
                    # --- CORREZIONE CRUCIALE QUI SOTTO ---
                    # Verifichiamo che la traccia esista E che abbia un album (salta i file locali/podcast)
                    if track and track.get('album') and track.get('artists'):
                        try:
                            # Gestione Immagine sicura
                            imgs = track['album']['images']
                            if len(imgs) > 0:
                                cover = imgs[0]['url']
                            else:
                                cover = "https://upload.wikimedia.org/wikipedia/commons/3/3c/No-album-art.png"

                            tracks.append({
                                "title": track['name'],
                                "artist": track['artists'][0]['name'],
                                "album": track['album']['name'],
                                "cover": cover
                            })
                        except Exception as e:
                            # Se una singola traccia dà errore, la saltiamo e stampiamo un avviso (senza rompere tutto)
                            print(f"⚠️ [Spotify] Saltata traccia problematica: {track.get('name')} - {e}")
                            continue
                
                if len(tracks) > 0:
                    print(f"✅ [Spotify] Scaricate {len(tracks)} tracce reali.")
                    return tracks, False # False = NON è demo

            except Exception as e:
                print(f"[Spotify] ERRORE CRITICO: {e}")

        # 2. DATASET DI BACKUP
        print("⚠️ [Spotify] Attivazione modalità DEMO (Backup).")
        backup_tracks = [
            {"title": "Bohemian Rhapsody", "artist": "Queen", "album": "A Night at the Opera", "cover": "https://upload.wikimedia.org/wikipedia/en/4/42/Queen_A_Night_At_The_Opera.png"},
            {"title": "Symphony No. 40", "artist": "Wolfgang Amadeus Mozart", "album": "Deutsche Grammophon", "cover": "https://upload.wikimedia.org/wikipedia/commons/1/1e/Wolfgang-amadeus-mozart_1.jpg"},
            {"title": "Smells Like Teen Spirit", "artist": "Nirvana", "album": "Nevermind", "cover": "https://upload.wikimedia.org/wikipedia/en/b/b7/NirvanaNevermindalbum.jpg"},
            {"title": "Bad Guy", "artist": "Billie Eilish", "album": "When We All Fall Asleep...", "cover": "https://upload.wikimedia.org/wikipedia/en/3/36/Billie_Eilish_-_When_We_All_Fall_Asleep%2C_Where_Do_We_Go%3F.png"},
            {"title": "Dynamite", "artist": "BTS", "album": "BE", "cover": "https://upload.wikimedia.org/wikipedia/en/d/d4/BTS_-_Dynamite.png"}
        ]
        
        return backup_tracks, True