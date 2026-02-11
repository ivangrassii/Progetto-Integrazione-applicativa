import requests

class WikiAgent:
    def __init__(self):
        self.url = "https://query.wikidata.org/sparql"

    def get_artist_data(self, artist_name):
        query = f"""
        SELECT ?item ?itemLabel ?description ?genreLabel ?placeLabel ?coords WHERE {{
          ?item rdfs:label "{artist_name}"@it.
          
          # DISAMBIGUAZIONE: Deve essere un'entità musicale (P31)
          ?item wdt:P31 ?type.
          FILTER (?type IN (wd:Q215380, wd:Q5)). 

          OPTIONAL {{ ?item schema:description ?description. FILTER(lang(?description) = "it") }}
          OPTIONAL {{ ?item wdt:P136 ?genre. ?genre rdfs:label ?genreLabel. FILTER(lang(?genreLabel) = "it") }}
          
          # DATI PER LA MAPPA (P19 luogo di nascita/origine e P625 coordinate)
          OPTIONAL {{ 
            ?item wdt:P19 ?place. 
            ?place wdt:P625 ?coords. 
            ?place rdfs:label ?placeLabel. FILTER(lang(?placeLabel) = "it") 
          }}
          
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "it". }}
        }} LIMIT 1
        """
        r = requests.get(self.url, params={'query': query, 'format': 'json'})
        data = r.json()
        results = data['results']['bindings']
        return results[0] if results else None