import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
import os

class SpotifyHandler:
    def __init__(self, client_id, client_secret):
        self.sp = None
        self.active = False
        
        # 1. Calcola il percorso per la cache (cartella principale del progetto)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        cache_path = os.path.join(project_root, ".spotify_cache")

        if client_id and client_secret:
            try:
                # 2. Autenticazione Robusta (Login Utente)
                # Questo è fondamentale per leggere le tue playlist private/pubbliche senza errori
                auth_manager = SpotifyOAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri="http://127.0.0.1:5000/callback",
                    scope="playlist-read-private playlist-read-collaborative",
                    cache_path=cache_path,
                    open_browser=False # False perché il server è già avviato
                )
                
                self.sp = spotipy.Spotify(auth_manager=auth_manager)
                
                # Test connessione immediato
                user = self.sp.current_user()
                print(f"✅ Spotify Connesso come: {user['display_name']}")
                self.active = True
                
            except Exception as e:
                print(f"❌ Errore Auth Spotify: {e}")
                self.active = False

    def extract_id_from_url(self, url):
        """Estrae l'ID pulito dall'URL."""
        if not url: return "demo"
        try:
            url = url.strip().split('?')[0]
            match = re.search(r"playlist[/:]([a-zA-Z0-9]+)", url)
            return match.group(1) if match else "demo"
        except:
            return "demo"

    def get_playlist_tracks(self, playlist_id):
        """Scarica i brani usando la logica universale 'Script Indipendente'."""
        tracks = []
        
        # Se non siamo attivi o l'ID è demo, restituisci dati finti
        if not self.active or playlist_id == "demo":
            return self._get_backup_data(), True

        try:
            print(f"🔄 Scarico playlist ID: {playlist_id}...")
            
            # --- LOGICA VINCENTE DELLO SCRIPT ESTERNO ---
            
            # 1. Scarica tutto l'oggetto con market="IT" (Evita errori 403 su brani locali/regionali)
            data = self.sp.playlist(playlist_id, market="IT")
            
            # 2. Cerca dove sono nascosti i brani (Struttura variabile)
            paginator = None
            if 'tracks' in data and isinstance(data['tracks'], dict):
                paginator = data['tracks'] # Caso Standard
            elif 'items' in data and isinstance(data['items'], dict):
                paginator = data['items']  # Caso del tuo JSON
            else:
                print("❌ Errore Struttura: Non trovo 'tracks' né 'items'.")
                return self._get_backup_data(), True

            # 3. Estrai la lista grezza
            raw_items = paginator.get('items', [])
            
            # 4. Paginazione: Scarica il resto se ce n'è (Gestisce playlist lunghe)
            while paginator['next']:
                paginator = self.sp.next(paginator)
                raw_items.extend(paginator['items'])

            print(f"✅ Trovati {len(raw_items)} brani totali.")

            # 5. Pulizia e Parsing dei dati
            for item in raw_items:
                # A volte è dentro 'track', a volte 'item', a volte diretto
                track = item.get('track')
                if not track: track = item.get('item')
                
                # Filtri di sicurezza:
                # - Deve avere un ID
                # - Deve essere di tipo 'track' (no podcast)
                # - Non deve essere un file locale (is_local=False)
                if track and track.get('id') and track.get('type') == 'track' and not track.get('is_local'):
                    
                    # Gestione sicura Immagine
                    cover = "https://via.placeholder.com/150"
                    try:
                        if track['album']['images']:
                            cover = track['album']['images'][0]['url']
                    except: pass
                    
                    # Gestione sicura Artista
                    artist = "Sconosciuto"
                    try:
                        if track['artists']:
                            artist = track['artists'][0]['name']
                    except: pass

                    tracks.append({
                        "title": track['name'],
                        "artist": artist,
                        "album": track['album']['name'],
                        "cover": cover,
                        "id": track['id']
                    })
            
            return tracks, False # False = Dati Reali

        except Exception as e:
            print(f"❌ ERRORE LETTURA FLASK: {e}")
            return self._get_backup_data(), True

    def _get_backup_data(self):
        """Dati di fallback in caso di errore critico."""
        return [
            {
                "title": "Bohemian Rhapsody", 
                "artist": "Queen", 
                "album": "A Night at the Opera", 
                "cover": ""
            },
            {
                "title": "Starman", 
                "artist": "David Bowie", 
                "album": "The Rise and Fall of Ziggy Stardust", 
                "cover": ""
            },
            {
                "title": "Can't Help Falling in Love", 
                "artist": "Elvis Presley", 
                "album": "Blue Hawaii", 
                "cover": ""
            },
            {
                "title": "Smells Like Teen Spirit", 
                "artist": "Nirvana", 
                "album": "Nevermind", 
                "cover": ""
            },
            {
                "title": "Bad Guy", 
                "artist": "Billie Eilish", 
                "album": "When We All Fall Asleep...", 
                "cover": ""
            },
            {
                "title": "Blinding Lights", 
                "artist": "The Weeknd", 
                "album": "After Hours", 
                "cover": ""
            },
            {
                "title": "Dynamite", 
                "artist": "BTS", 
                "album": "BE", 
                "cover": ""
            },
            {
                "title": "So What", 
                "artist": "Miles Davis", 
                "album": "Kind of Blue", 
                "cover": ""
            },
            {
                "title": "Get Lucky", 
                "artist": "Daft Punk", 
                "album": "Random Access Memories", 
                "cover": ""
            },
            {
                "title": "Rolling in the Deep", 
                "artist": "Adele", 
                "album": "21", 
                "cover": ""
            },
            {
                "title": "Hotel California", 
                "artist": "Eagles", 
                "album": "Hotel California", 
                "cover": ""
            },
            {
                "title": "Imagine", 
                "artist": "John Lennon", 
                "album": "Imagine", 
                "cover": ""
            }
        ]     
        return backup_tracks, True