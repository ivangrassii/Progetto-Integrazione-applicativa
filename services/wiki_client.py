import requests

class WikiAgent:
    def __init__(self):
        self.url = "https://query.wikidata.org/sparql"
        self.headers = {
            'User-Agent': 'IMKB-APP/7.0',
            'Accept': 'application/sparql-results+json'
        }

    def get_artist_data(self, artist_name):
        query = f"""
        SELECT ?item ?itemLabel ?description ?genreLabel ?placeLabel ?coords WHERE {{
          ?item rdfs:label "{artist_name}"@it.
          ?item wdt:P31 ?type.
          FILTER (?type IN (wd:Q215380, wd:Q5)). 
          OPTIONAL {{ ?item schema:description ?description. FILTER(lang(?description) = "it") }}
          OPTIONAL {{ ?item wdt:P136 ?genre. ?genre rdfs:label ?genreLabel. FILTER(lang(?genreLabel) = "it") }}
          OPTIONAL {{ 
            ?item wdt:P19 ?place. 
            ?place wdt:P625 ?coords. 
            ?place rdfs:label ?placeLabel. FILTER(lang(?placeLabel) = "it") 
          }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "it". }}
        }} LIMIT 1
        """
        try:
            r = requests.get(self.url, params={'query': query, 'format': 'json'}, headers=self.headers)
            r.raise_for_status()
            data = r.json()
            results = data['results']['bindings']
            return results[0] if results else None
        except Exception as e:
            print(f"Errore SPARQL Artista: {e}")
            return None

    def get_track_url(self, title, artist):
        
        # Pulizia nomi per la query
        clean_title = title.replace('"', '').replace("'", "")
        clean_artist = artist.replace('"', '').replace("'", "")
        
        query = f"""
        SELECT DISTINCT ?canzone WHERE {{
          # Usa 'clean_title' perché 'track_name' non è definita
          ?canzone rdfs:label "{clean_title}"@it. 
          
          # Usa 'clean_artist'
          ?canzone wdt:P175 ?artista.
          ?artista rdfs:label "{clean_artist}"@it.

          # Filtro per opere musicali o sottoclassi
          ?canzone wdt:P31/wdt:P279* wd:Q2188189. 
        }} LIMIT 1
        """
        try:
            r = requests.get(self.url, params={'query': query, 'format': 'json'}, headers=self.headers)
            r.raise_for_status()
            data = r.json()
            results = data.get('results', {}).get('bindings', [])
            return results[0]['canzone']['value'] if results else None
        except Exception as e:
            print(f"Errore SPARQL: {e}")
            return None

    def get_entity_details(self, entity_url):
        query = f"""
        SELECT ?canzoneLabel 
               (MAX(?immagine) AS ?img) 
               (MAX(?dataPubblicazione) AS ?data) 
               (GROUP_CONCAT(DISTINCT ?genereLabel; separator="|") AS ?generi) 
               (GROUP_CONCAT(DISTINCT ?produttoreLabel; separator="|") AS ?produttori) 
               (GROUP_CONCAT(DISTINCT ?premioLabel; separator="|") AS ?premi) 
               (GROUP_CONCAT(DISTINCT ?artistaLabel; separator="|") AS ?artisti)
        WHERE {{
          BIND(<{entity_url}> AS ?canzone)
          OPTIONAL {{ ?canzone rdfs:label ?canzoneLabel . FILTER(lang(?canzoneLabel)="it" || lang(?canzoneLabel)="en") }}
          OPTIONAL {{ ?canzone wdt:P18 ?immagine . }}
          OPTIONAL {{ ?canzone wdt:P577|wdt:P571 ?dataPubblicazione . }}
          OPTIONAL {{ ?canzone wdt:P136 ?g . ?g rdfs:label ?genereLabel . FILTER(lang(?genereLabel)="it" || lang(?genereLabel)="en") }}
          OPTIONAL {{ ?canzone wdt:P162 ?p . ?p rdfs:label ?produttoreLabel . FILTER(lang(?produttoreLabel)="it" || lang(?produttoreLabel)="en") }}
          OPTIONAL {{ ?canzone wdt:P166 ?pr . ?pr rdfs:label ?premioLabel . FILTER(lang(?premioLabel)="it" || lang(?premioLabel)="en") }}
          OPTIONAL {{ ?canzone wdt:P175 ?a . ?a rdfs:label ?artistaLabel . FILTER(lang(?artistaLabel)="it" || lang(?artistaLabel)="en") }}
        }}
        GROUP BY ?canzoneLabel
        """
        try:
            r = requests.get(self.url, params={'query': query}, headers=self.headers)
            r.raise_for_status()
            results = r.json().get('results', {}).get('bindings', [])
            
            if results:
                res = results[0]
                img_url = res.get('img', {}).get('value')
                artisti_str = res.get('artisti', {}).get('value', '')
                collaborators_list = artisti_str.split('|') if artisti_str else []

                return {
                    'found': True,
                    'wikidata_url': entity_url,
                    'official_title': res.get('canzoneLabel', {}).get('value', 'Sconosciuto'),
                    'image': img_url if img_url else None, # Se non c'è, torna None
                    'genre': res.get('generi', {}).get('value', '').replace('|', ', ') or 'Non specificato',
                    'producer': res.get('produttori', {}).get('value', '').replace('|', ', ') or 'Non specificato',
                    'awards': res.get('premi', {}).get('value', '').replace('|', ', ') or 'Nessun premio registrato',
                    'date': res.get('data', {}).get('value', '').split('T')[0] if 'data' in res else 'Non specificata',
                    'collaborators': collaborators_list
                }
            return {'found': False, 'image': None, 'collaborators': []}
        except Exception as e:
            return {'found': False, 'image': None, 'collaborators': []}