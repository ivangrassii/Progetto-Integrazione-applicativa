import requests
import sys

class WikiAgent:
    def __init__(self):
        # Endpoint di Wikidata
        self.url = "https://query.wikidata.org/sparql"
        # User-Agent necessario per non essere bloccati dai server
        self.headers = {
            'User-Agent': 'IntegrazioneApplicativaBot/1.0',
            'Accept': 'application/sparql-results+json'
        }

    def get_info(self, concetto):
        """Metodo che funge da SENSORE per percepire dati dal web."""
        query = f"""
        SELECT ?desc WHERE {{
          ?item rdfs:label "{concetto}"@it.
          ?item schema:description ?desc.
          FILTER(lang(?desc) = "it")
        }} LIMIT 1
        """
        try:
            response = requests.get(self.url, params={'query': query, 'format': 'json'}, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            risultati = data.get("results", {}).get("bindings", [])
            if risultati:
                return risultati[0]["desc"]["value"]
            else:
                return "Nessuna descrizione trovata per questo concetto."
        except Exception as e:
            return f"Errore di rete o di connessione: {e}"

# --- LOGICA DELL'AGENTE ---
if __name__ == "__main__":
    agente = WikiAgent()
    print("Agente di Integrazione Pronto!")
    
    while True:
        scelta = input("\nCosa vuoi cercare su Wikidata? (scrivi 'esci' per chiudere): ")
        if scelta.lower() == 'esci':
            print("Agente disattivato. Ciao!")
            break
        
        print(f"L'agente sta percependo dati per: {scelta}...")
        risultato = agente.get_info(scelta)
        
        # L'azione dell'agente: visualizzare l'informazione (Attuatore)
        print(f" RISULTATO: {risultato}")