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
        Fase 1: Trova l'URL Wikidata della canzone usando il servizio mwapi (EntitySearch).
        Questo metodo evita il timeout e risolve i problemi di etichette multilingua.
        """
        # Pulizia per evitare che le virgolette rompano la sintassi SPARQL
        clean_title = title.replace('"', '')
        clean_artist = artist.replace('"', '')
        
        query = f"""
        SELECT DISTINCT ?canzone WHERE {{
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
          
          # Verifica che sia un'opera musicale o sottoclasse (es. canzone, singolo)
          ?canzone wdt:P31/wdt:P279* wd:Q2188189 . 
        }} LIMIT 1
        """
        try:
            # Effettua la richiesta al server Wikidata
            r = requests.get(self.url, params={'query': query, 'format': 'json'}, headers=self.headers)
            r.raise_for_status()
            data = r.json()
            
            results = data.get('results', {}).get('bindings', [])
            
            # Se troviamo un risultato, restituiamo l'URL dell'entità
            if results:
                return results[0]['canzone']['value']
            
            # Se non trova nulla, restituiamo None
            return None
            
        except Exception as e:
            print(f"Errore nel recupero URL tramite mwapi: {e}")
            return None

    def get_track_details(self, entity_url):
        """
        Estrae i dettagli gestendo correttamente MULTIPLI artisti.
        Usa una logica di 'impacchettamento' stringa direttamente in SPARQL.
        """
        # Assicuriamoci che l'URL sia nel formato <URL> per SPARQL
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
            # Qui sta il trucco: uniamo tutti gli artisti trovati in un'unica stringa separata da "||"
            (GROUP_CONCAT(DISTINCT ?artistPack; separator="||") AS ?artisti)
            WHERE {{
            # Sostituisci qui con l'URL o l'ID della canzone
            BIND({entity_url} AS ?song) . 

            # Dati semplici
            OPTIONAL {{ ?song wdt:P18 ?img . }}
            OPTIONAL {{ ?song wdt:P577 ?data . }}
            OPTIONAL {{ ?song wdt:P136 ?genere . }}
            OPTIONAL {{ ?song wdt:P162 ?produttore . }}
            OPTIONAL {{ ?song wdt:P166 ?premio . }}

            # RECUPERO ARTISTI (Gestione Multipla)
            OPTIONAL {{
                ?song wdt:P175 ?artist .
                # Trucco per forzare il recupero della label SPECIFICA per ogni artista trovato
                OPTIONAL {{
                    ?artist rdfs:label ?rawArtistLabel .
                    FILTER(LANG(?rawArtistLabel) = "it")
                }}
                OPTIONAL {{
                    ?artist rdfs:label ?rawArtistLabelEn .
                    FILTER(LANG(?rawArtistLabelEn) = "en")
                }}
                # Se non c'è label IT o EN, usa l'URL come nome (fallback)
                BIND(COALESCE(?rawArtistLabel, ?rawArtistLabelEn, STR(?artist)) AS ?finalArtistName)
                
                # Creiamo il pacchetto "Nome::URL" SUBITO, prima di uscire dal blocco
                BIND(CONCAT(?finalArtistName, "::", STR(?artist)) AS ?artistPack)
            }}

            # Servizio label per tutto il resto (generi, produttori...)
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
            
            # --- PARSING DEGLI ARTISTI ---
            # La stringa arriva come: "Elvis Presley::http://...||The Jordanaires::http://..."
            artisti_raw = res.get('artisti', {}).get('value', '')
            lista_artisti = []
            
            if artisti_raw:
                # 1. Separiamo i vari artisti usando '||'
                for item in artisti_raw.split('||'):
                    # 2. Separiamo Nome da URL usando '::'
                    if '::' in item:
                        parts = item.split('::')
                        # Gestione sicurezza se ci fossero più '::' nel nome
                        nome = parts[0]
                        url = "".join(parts[1:]) 
                        lista_artisti.append({'name': nome, 'url': url})
            
            # Se la lista è vuota (caso raro), mettiamo un placeholder
            if not lista_artisti:
                 lista_artisti.append({'name': 'Artista Sconosciuto', 'url': ''})

            return {
                'found': True,
                'wikidata_url': entity_url.replace('<','').replace('>',''),
                'title': res.get('songLabel', {}).get('value', 'Titolo Sconosciuto'),
                'image': res.get('immagine', {}).get('value', None),
                'date': res.get('dataUscita', {}).get('value', '').split('T')[0],
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