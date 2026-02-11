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
        clean_title = title.replace('"', '').replace("'", "")
        clean_artist = artist.replace('"', '').replace("'", "")
        
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
        query = f"""
        SELECT ?canzoneLabel 
               (MAX(?immagine) AS ?img) 
               (MAX(?dataPubblicazione) AS ?data) 
               (GROUP_CONCAT(DISTINCT ?genereLabel; separator="|") AS ?generi) 
               (GROUP_CONCAT(DISTINCT ?produttoreLabel; separator="|") AS ?produttori) 
               (GROUP_CONCAT(DISTINCT ?premioLabel; separator="|") AS ?premi)
               (GROUP_CONCAT(DISTINCT ?artistaInfo; separator="||") AS ?artisti)
        WHERE {{
          BIND(<{entity_url}> AS ?canzone)
          
          # Label della canzone con priorità IT > EN
          OPTIONAL {{
            ?canzone rdfs:label ?labelIT . FILTER(lang(?labelIT) = "it")
          }}
          OPTIONAL {{
            ?canzone rdfs:label ?labelEN . FILTER(lang(?labelEN) = "en")
          }}
          BIND(COALESCE(?labelIT, ?labelEN, "Sconosciuto") AS ?canzoneLabel)

          OPTIONAL {{ ?canzone wdt:P18 ?immagine . }}
          OPTIONAL {{ ?canzone wdt:P577|wdt:P571 ?dataPubblicazione . }}

          # Generi: Cerchiamo IT, se manca usiamo EN
          OPTIONAL {{ 
            ?canzone wdt:P136 ?g . 
            OPTIONAL {{ ?g rdfs:label ?gIT . FILTER(lang(?gIT) = "it") }}
            OPTIONAL {{ ?g rdfs:label ?gEN . FILTER(lang(?gEN) = "en") }}
            BIND(COALESCE(?gIT, ?gEN) AS ?genereLabel)
          }}

          # Produttori: Cerchiamo IT, se manca usiamo EN
          OPTIONAL {{ 
            ?canzone wdt:P162 ?p . 
            OPTIONAL {{ ?p rdfs:label ?pIT . FILTER(lang(?pIT) = "it") }}
            OPTIONAL {{ ?p rdfs:label ?pEN . FILTER(lang(?pEN) = "en") }}
            BIND(COALESCE(?pIT, ?pEN) AS ?produttoreLabel)
          }}

          # Premi: Cerchiamo IT, se manca usiamo EN
          OPTIONAL {{ 
            ?canzone wdt:P166 ?pr . 
            OPTIONAL {{ ?pr rdfs:label ?prIT . FILTER(lang(?prIT) = "it") }}
            OPTIONAL {{ ?pr rdfs:label ?prEN . FILTER(lang(?prEN) = "en") }}
            BIND(COALESCE(?prIT, ?prEN) AS ?premioLabel)
          }}
          
          # Artisti: Cerchiamo IT, se manca usiamo EN
          OPTIONAL {{ 
            ?canzone wdt:P175 ?a . 
            OPTIONAL {{ ?a rdfs:label ?aIT . FILTER(lang(?aIT) = "it") }}
            OPTIONAL {{ ?a rdfs:label ?aEN . FILTER(lang(?aEN) = "en") }}
            BIND(COALESCE(?aIT, ?aEN) AS ?aLabel)
            BIND(CONCAT(STR(?aLabel), ">", STR(?a)) AS ?artistaInfo)
          }}
        }}
        GROUP BY ?canzoneLabel
        """
        try:
            r = requests.get(self.url, params={'query': query, 'format': 'json'}, headers=self.headers)
            r.raise_for_status()
            results = r.json().get('results', {}).get('bindings', [])
            
            if results:
                res = results[0]
                artisti_raw = res.get('artisti', {}).get('value', '').split('||')
                lista_artisti = []
                # Set per evitare duplicati di URL artista (stessa persona con label IT ed EN)
                seen_artists = set()
                
                for item in artisti_raw:
                    if '>' in item:
                        nome, url = item.split('>')
                        if url not in seen_artists:
                            lista_artisti.append({'name': nome, 'url': url})
                            seen_artists.add(url)

                return {
                    'found': True,
                    'wikidata_url': entity_url,
                    'title': res.get('canzoneLabel', {}).get('value', 'Sconosciuto'),
                    'image': res.get('img', {}).get('value'),
                    'date': res.get('data', {}).get('value', '').split('T')[0] if 'data' in res else 'N/D',
                    'genres': res.get('generi', {}).get('value', '').replace('|', ', ') or 'N/D',
                    'producers': res.get('produttori', {}).get('value', '').replace('|', ', ') or 'N/D',
                    'awards': res.get('premi', {}).get('value', '').replace('|', ', ') or 'Nessuno',
                    'artisti_list': lista_artisti
                }
            return {'found': False}
        except Exception as e:
            print(f"Errore: {e}")
            return {'found': False}

