import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re

class SpotifyHandler:
    def __init__(self, client_id, client_secret):
        self.sp = None
        self.active = False
        
        if client_id and client_secret:
            try:
                auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
                self.sp = spotipy.Spotify(auth_manager=auth_manager)
                self.active = True
            except:
                self.active = False

    def extract_id_from_url(self, url):
        if not url: return "demo"
        try:
            # Pulisce eventuali parametri di tracciamento
            url = url.strip().split('?')[0]
            # Migliorato: ora accetta sia "playlist/ID" che "playlist:ID"
            match = re.search(r"playlist[/:]([a-zA-Z0-9]+)", url)
            return match.group(1) if match else "demo"
        except:
            return "demo"

    def get_playlist_tracks(self, playlist_id):
        tracks = []
        
        # 1. TENTATIVO API (Dati Reali)
        if self.active:
            try:
                # Scarica il primo blocco di risultati
                results = self.sp.playlist_items(playlist_id)
                items = results.get('items', [])
                
                # LA MAGIA DELLA PAGINAZIONE: Continua a scaricare finché ci sono pagine successive!
                while results['next']:
                    results = self.sp.next(results)
                    items.extend(results['items'])
                
                for item in items:
                    track = item.get('track')
                    if track:
                        # Gestione Immagine (Prendiamo la media, index 1, o la prima disponibile)
                        imgs = track['album']['images']
                        if len(imgs) > 1:
                            cover = imgs[1]['url'] 
                        elif len(imgs) > 0:
                            cover = imgs[0]['url']
                        else:
                            cover = "https://upload.wikimedia.org/wikipedia/commons/3/3c/No-album-art.png"

                        tracks.append({
                            "title": track['name'],
                            "artist": track['artists'][0]['name'],
                            "album": track['album']['name'],
                            "cover": cover
                        })
                
                if len(tracks) > 0:
                    return tracks, False # False = Dati Reali

            except Exception as e:
                print(f"Errore API Spotify: {e}") # Stampa l'errore nel terminale per aiutarti a capire cosa è andato storto
                pass # Se fallisce, va al backup silenziosamente

        # 2. DATASET DI BACKUP (Se le API falliscono)
        backup_tracks = [
            {"title": "Bohemian Rhapsody", "artist": "Queen", "album": "A Night at the Opera", "cover": "https://upload.wikimedia.org/wikipedia/en/4/42/Queen_A_Night_At_The_Opera.png"},
            {"title": "Symphony No. 40", "artist": "Wolfgang Amadeus Mozart", "album": "Deutsche Grammophon", "cover": "https://upload.wikimedia.org/wikipedia/commons/1/1e/Wolfgang-amadeus-mozart_1.jpg"},
            {"title": "Smells Like Teen Spirit", "artist": "Nirvana", "album": "Nevermind", "cover": "https://upload.wikimedia.org/wikipedia/en/b/b7/NirvanaNevermindalbum.jpg"},
            {"title": "Bad Guy", "artist": "Billie Eilish", "album": "When We All Fall Asleep...", "cover": "https://upload.wikimedia.org/wikipedia/en/3/36/Billie_Eilish_-_When_We_All_Fall_Asleep%2C_Where_Do_We_Go%3F.png"},
            {"title": "Dynamite", "artist": "BTS", "album": "BE", "cover": "https://upload.wikimedia.org/wikipedia/en/d/d4/BTS_-_Dynamite.png"}
        ]
        
        return backup_tracks, True