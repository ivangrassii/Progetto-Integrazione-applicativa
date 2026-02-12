import requests

class WikiAgent:
    def __init__(self):
        # Endpoint ufficiale per le query SPARQL di Wikidata
        self.url = "https://query.wikidata.org/sparql"
        # User-Agent è obbligatorio per evitare blocchi dalle API di Wikidata
        self.headers = {
            'User-Agent': 'MusicDataBot/1.0 (https://example.com; contact@example.com)',
            'Accept': 'application/sparql-results+json'
        }

    def get_track_url(self, title, artist):
        """
        Fase 1: Trova l'URL Wikidata della canzone E dell'artista.
        Restituisce una tupla: (track_url, artist_url)
        """
        # Pulizia per evitare che le virgolette rompano la sintassi SPARQL
        clean_title = title.replace('"', '')
        clean_artist = artist.replace('"', '')
        
        # MODIFICA 1: Aggiunto ?artista alla SELECT
        query = f"""
        SELECT DISTINCT ?canzone ?artista WHERE {{
          # Cerca l'artista tramite motore di ricerca interno
          SERVICE wikibase:mwapi {{
              bd:serviceParam wikibase:api "EntitySearch" .
              bd:serviceParam wikibase:endpoint "www.wikidata.org" .
              bd:serviceParam mwapi:search "{clean_artist}" .
              bd:serviceParam mwapi:language "it" .
              ?artista wikibase:apiOutputItem mwapi:item .
          }}
          
          # Cerca la canzone tramite motore di ricerca interno
          SERVICE wikibase:mwapi {{
              bd:serviceParam wikibase:api "EntitySearch" .
              bd:serviceParam wikibase:endpoint "www.wikidata.org" .
              bd:serviceParam mwapi:search "{clean_title}" .
              bd:serviceParam mwapi:language "it" .
              ?canzone wikibase:apiOutputItem mwapi:item .
          }}

          # Verifica che la canzone sia effettivamente collegata all'artista
          ?canzone wdt:P175 ?artista .
          
          # Verifica che sia un'opera musicale o sottoclasse
          ?canzone wdt:P31/wdt:P279* wd:Q2188189 . 
        }} LIMIT 1
        """
        try:
            r = requests.get(self.url, params={'query': query, 'format': 'json'}, headers=self.headers)
            r.raise_for_status()
            data = r.json()
            
            results = data.get('results', {}).get('bindings', [])
            
            # MODIFICA 2: Restituiamo entrambi i valori
            if results:
                song_url = results[0]['canzone']['value']
                artist_url = results[0]['artista']['value']
                return song_url, artist_url
            
            return None, None
            
        except Exception as e:
            print(f"Errore nel recupero URL tramite mwapi: {e}")
            return None, None

    def get_track_details(self, entity_url):
        """
        Versione ROBUSTA: Recupera il nome dell'artista in qualsiasi lingua disponibile
        se mancano IT ed EN.
        """
        if not entity_url.startswith('<'):
            entity_url = f"<{entity_url}>"

        query = f"""
        SELECT 
          ?songLabel
          (SAMPLE(?img) AS ?immagine)
          (MIN(?data) AS ?dataUscita) 
          (GROUP_CONCAT(DISTINCT ?genereLabel; separator=", ") AS ?generi)
          (GROUP_CONCAT(DISTINCT ?produttoreLabel; separator=", ") AS ?produttori)
          (GROUP_CONCAT(DISTINCT ?premioLabel; separator=", ") AS ?premi)
          (GROUP_CONCAT(DISTINCT ?artistPack; separator="||") AS ?artisti)
        WHERE {{
          BIND({entity_url} AS ?song) . 

          OPTIONAL {{ ?song wdt:P18 ?img . }}
          OPTIONAL {{ ?song wdt:P577 ?data . }}
          OPTIONAL {{ ?song wdt:P136 ?genere . }}
          OPTIONAL {{ ?song wdt:P162 ?produttore . }}
          OPTIONAL {{ ?song wdt:P166 ?premio . }}

          # --- RECUPERO ARTISTI (Versione "Prendi Tutto") ---
          OPTIONAL {{ 
            ?song wdt:P175 ?artist .
            
            # 1. Tentativo IT
            OPTIONAL {{ ?artist rdfs:label ?labelIT . FILTER(LANG(?labelIT) = "it") }}
            
            # 2. Tentativo EN
            OPTIONAL {{ ?artist rdfs:label ?labelEN . FILTER(LANG(?labelEN) = "en") }}
            
            # 3. Tentativo "Qualsiasi Lingua" (Prendiamo una label a caso se esistono)
            OPTIONAL {{ ?artist rdfs:label ?labelANY . }}

            # COALESCE: Prende il primo valore NON nullo della lista
            BIND(COALESCE(?labelIT, ?labelEN, ?labelANY, STR(?artist)) AS ?finalName)
            
            # Creiamo il pacchetto
            BIND(CONCAT(?finalName, "::", STR(?artist)) AS ?artistPack)
          }}
          # --------------------------------------------------

          SERVICE wikibase:label {{ 
            bd:serviceParam wikibase:language "it,en". 
            ?song rdfs:label ?songLabel .
            ?genere rdfs:label ?genereLabel .
            ?produttore rdfs:label ?produttoreLabel .
            ?premio rdfs:label ?premioLabel .
          }}
        }}
        GROUP BY ?songLabel
        """
        
        try:
            r = requests.get(self.url, params={'query': query, 'format': 'json'}, headers=self.headers)
            r.raise_for_status()
            results = r.json().get('results', {}).get('bindings', [])
            
            if not results:
                return {'found': False}

            res = results[0]
            
            # --- Parsing Artisti ---
            artisti_raw = res.get('artisti', {}).get('value', '')
            lista_artisti = []
            
            if artisti_raw:
                # Usiamo un set per evitare duplicati se la logica ANY trova più label
                nomi_visti = set() 
                
                for item in artisti_raw.split('||'):
                    if '::' in item:
                        parts = item.split('::')
                        nome = parts[0]
                        # Ricostruisce URL (gestisce casi con :: nel nome)
                        url = "::".join(parts[1:])
                        
                        # Aggiungiamo solo se non abbiamo già inserito questo URL
                        if url not in nomi_visti and nome and url:
                            lista_artisti.append({'name': nome, 'url': url})
                            nomi_visti.add(url)
            
            if not lista_artisti:
                 lista_artisti.append({'name': 'Artista Sconosciuto', 'url': ''})

            return {
                'found': True,
                'wikidata_url': entity_url.replace('<','').replace('>',''),
                'title': res.get('songLabel', {}).get('value', 'Titolo Sconosciuto'),
                'image': res.get('immagine', {}).get('value', None),
                'date': res.get('dataUscita', {}).get('value', '').split('T')[0] if 'dataUscita' in res else 'N/D',
                'genres': res.get('generi', {}).get('value', 'N/D'),
                'producers': res.get('produttori', {}).get('value', 'N/D'),
                'awards': res.get('premi', {}).get('value', 'Nessuno'),
                'artisti_list': lista_artisti
            }
            
        except Exception as e:
            print(f"Errore Get Details: {e}")
            return {'found': False}


    def get_artist_details(self, entity_url):
        """
        Estrae i dettagli di un artista partendo dal suo URL Wikidata (QID).
        """
        query = f"""
        SELECT ?nome 
               (MAX(?immagine) AS ?img)
               (MAX(?bio) AS ?desc)
               (MAX(?nascita) AS ?dataNascita)
               (MAX(?morte) AS ?dataMorte)
               (MAX(?luogoLabel) AS ?luogo)
               (GROUP_CONCAT(DISTINCT ?genereLabel; separator=", ") AS ?generi)
        WHERE {{
          BIND(<{entity_url}> AS ?artista)
          
          # Nome con priorità Italiano > Inglese
          OPTIONAL {{ ?artista rdfs:label ?nIT . FILTER(lang(?nIT) = "it") }}
          OPTIONAL {{ ?artista rdfs:label ?nEN . FILTER(lang(?nEN) = "en") }}
          BIND(COALESCE(?nIT, ?nEN) AS ?nome)

          # Biografia/Descrizione breve
          OPTIONAL {{ ?artista schema:description ?bio . FILTER(lang(?bio) = "it") }}
          
          # Immagine
          OPTIONAL {{ ?artista wdt:P18 ?immagine . }}
          
          # Date
          OPTIONAL {{ ?artista wdt:P569 ?nascita . }}
          OPTIONAL {{ ?artista wdt:P570 ?morte . }}
          
          # Luogo (nascita o origine)
          OPTIONAL {{ 
            ?artista wdt:P19|wdt:P740 ?l . 
            ?l rdfs:label ?luogoLabel . FILTER(lang(?luogoLabel) = "it") 
          }}
          
          # Generi
          OPTIONAL {{ 
            ?artista wdt:P136 ?g . 
            ?g rdfs:label ?genereLabel . FILTER(lang(?genereLabel) = "it") 
          }}
        }}
        GROUP BY ?nome
        """
        try:
            r = requests.get(self.url, params={'query': query, 'format': 'json'}, headers=self.headers)
            r.raise_for_status()
            results = r.json().get('results', {}).get('bindings', [])
            
            if results:
                res = results[0]
                return {
                    'found': True,
                    'name': res.get('nome', {}).get('value', 'Sconosciuto'),
                    'image': res.get('img', {}).get('value'),
                    'description': res.get('desc', {}).get('value', 'Nessuna biografia disponibile su Wikidata.'),
                    'birth': res.get('dataNascita', {}).get('value', '').split('T')[0] if 'dataNascita' in res else None,
                    'death': res.get('dataMorte', {}).get('value', '').split('T')[0] if 'dataMorte' in res else None,
                    'origin': res.get('luogo', {}).get('value', 'Non specificato'),
                    'genres': res.get('generi', {}).get('value', 'Non specificato'),
                    'url': entity_url
                }
            return {'found': False}
        except Exception as e:
            print(f"Errore nel recupero dell'artista: {e}")
            return {'found': False}

    def get_recommendations(self, song_url, artist_url):
        if not song_url or not artist_url: return []

        song_id = song_url.split('/')[-1]
        artist_id = artist_url.split('/')[-1]
        
        # Query Ottimizzata Anti-Timeout
        query = f"""
        SELECT DISTINCT ?song ?songLabel ?artist ?artistLabel ?image ?type WHERE {{
          # INPUT
          BIND(wd:{song_id} AS ?inputSong) .
          BIND(wd:{artist_id} AS ?inputArtist) .

          # --- BLOCCO 1: Fan Choice (Stesso Artista) ---
          {{
            SELECT DISTINCT ?song ?artistLabel ?type WHERE {{
                BIND(wd:{song_id} AS ?inputSong) .
                BIND(wd:{artist_id} AS ?inputArtist) .
                ?song wdt:P31 wd:Q7366 ; wdt:P175 ?inputArtist.
                FILTER(?song != ?inputSong)
                BIND("Fan Choice" AS ?type)
                BIND("Stesso Artista" AS ?artistLabel)
            }} LIMIT 5
          }}
          UNION
          # --- BLOCCO 2: Discovery (Genere + Filtro Data Opzionale) ---
          {{
             SELECT DISTINCT ?song ?artistLabel ?type WHERE {{
                BIND(wd:{song_id} AS ?inputSong) .
                BIND(wd:{artist_id} AS ?inputArtist) .
                
                # 1. Prendi genere e data input
                ?inputSong wdt:P136 ?targetGenre .
                OPTIONAL {{ ?inputSong wdt:P577 ?inputDate . }}
                BIND(YEAR(?inputDate) AS ?inputYear)

                # 2. Cerca per GENERE (Veloce)
                ?song wdt:P136 ?targetGenre ;
                      wdt:P31 wd:Q7366 ;
                      wdt:P175 ?artist .
                
                FILTER(?song != ?inputSong)
                FILTER(?artist != ?inputArtist)

                # 3. Filtro Data Intelligente (Se c'è, usala. Se no, passa.)
                OPTIONAL {{ ?song wdt:P577 ?songDate . }}
                BIND(YEAR(?songDate) AS ?songYear)
                
                FILTER(
                    !BOUND(?songDate) || 
                    !BOUND(?inputYear) || 
                    (?songYear >= (?inputYear - 4) && ?songYear <= (?inputYear + 4))
                )

                BIND("Discovery" AS ?type)
                ?artist rdfs:label ?artistLabel . FILTER(LANG(?artistLabel) = "en")
             }} LIMIT 5
          }}
          
          OPTIONAL {{ ?song wdt:P18 ?image }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en,it". }}
        }}
        """
        
        try:
            r = requests.get(self.url, params={'query': query, 'format': 'json'}, headers=self.headers)
            results = r.json().get('results', {}).get('bindings', [])
            recs = []
            seen = set()

            for res in results:
                title = res.get("songLabel", {}).get("value", "Titolo Sconosciuto")
                if title in seen: continue
                seen.add(title)
                
                rec_type = res["type"]["value"]
                
                # Gestione URL Artista:
                # Se è Fan Choice, usiamo l'URL originale (artist_url).
                # Se è Discovery, usiamo quello trovato nella query (?artist).
                if rec_type == "Fan Choice":
                    current_artist_url = artist_url # Quello che abbiamo passato alla funzione
                    artist_name = "Stesso Artista"
                else:
                    current_artist_url = res.get("artist", {}).get("value")
                    artist_name = res.get("artistLabel", {}).get("value", "Artista Simile")

                recs.append({
                    "title": title, 
                    "artist": artist_name, 
                    "type": rec_type,
                    "image": res.get("image", {}).get("value", "https://via.placeholder.com/150"),
                    # DATI FONDAMENTALI PER IL LINK DIRETTO:
                    "url": res["song"]["value"],       # ID Canzone (url wikidata)
                    "artist_url": current_artist_url   # ID Artista
                })
            return recs
        except Exception as e:
            print(f"❌ Errore Recs: {e}")
            return []