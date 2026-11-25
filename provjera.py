import json
import os
import re
import requests
from bs4 import BeautifulSoup

URL = "https://voda.ba"
PRAG_RASTA_CM = 1  # Šalje alarm čim poraste za >= 1 cm između dva mjerenja
EXPO_PUSH_TOKEN = os.environ.get("EXPO_PUSH_TOKEN", "").strip()

def posalji_push(naslov, poruka):
    if not EXPO_PUSH_TOKEN:
        print("EXPO_PUSH_TOKEN nije podešen u GitHub Secrets.")
        return
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {
        "to": EXPO_PUSH_TOKEN,
        "sound": "default",
        "title": naslov,
        "body": poruka,
        "priority": "high",
    }
    try:
        r = requests.post("https://exp.host", json=payload, headers=headers, timeout=15)
        print("Expo odgovor:", r.status_code, r.text)
    except Exception as e:
        print("Greška pri slanju push notifikacije:", e)

def izvuci_broj(tekst):
    match = re.search(r"-?\d+", tekst)
    return int(match.group()) if match else None

def main():
    try:
        with open("podaci.json", "r", encoding="utf-8") as f:
            stari_podaci = json.load(f)
    except Exception:
        stari_podaci = {"nivo": 0, "razlika": 0, "vrijeme": "", "istorija": []}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    odgovor = requests.get(URL, headers=headers, timeout=20)
    odgovor.raise_for_status()
    soup = BeautifulSoup(odgovor.text, "html.parser")

    trenutni_nivo = None
    vrijeme_mjerenja = ""

    for red in soup.find_all("tr"):
        kolone = [td.get_text(strip=True) for td in red.find_all("td")]
        if any("Kladanj" in k for k in kolone) and len(kolone) >= 5:
            vrijeme_mjerenja = kolone[2] if len(kolone) > 2 else ""
            for k in kolone[3:]:
                if "cm" in k.lower() or k.isdigit():
                    broj = izvuci_broj(k)
                    if broj is not None:
                        trenutni_nivo = broj
                        break
            if trenutni_nivo is not None:
                break

    if trenutni_nivo is None:
        print("Greška: Stanica HS Kladanj nije pronađena u tabeli na voda.ba.")
        return

    if vrijeme_mjerenja == stari_podaci.get("vrijeme"):
        print(f"Nema novog mjerenja ({vrijeme_mjerenja}). Trenutni nivo je i dalje {trenutni_nivo} cm.")
        return

    stari_nivo = stari_podaci.get("nivo", 0)
    razlika = (trenutni_nivo - stari_nivo) if stari_nivo > 0 else 0

    istorija = stari_podaci.get("istorija", [])
    istorija.append({"vrijeme": vrijeme_mjerenja, "nivo": trenutni_nivo})
    istorija = istorija[-24:]

    novi_podaci = {
        "nivo": trenutni_nivo,
        "razlika": razlika,
        "vrijeme": vrijeme_mjerenja,
        "istorija": istorija
    }

    with open("podaci.json", "w", encoding="utf-8") as f:
        json.dump(novi_podaci, f, ensure_ascii=False, indent=2)

    print(f"Uspješno ažurirano: {trenutni_nivo} cm (razlika: {razlika} cm, vrijeme: {vrijeme_mjerenja})")

    # Šalje Push notifikaciju čim poraste za 1 cm ili više
    if stari_nivo > 0 and razlika >= PRAG_RASTA_CM:
        posalji_push(
            "📈 Porast vodostaja Drinjače!",
            f"Nivo u Kladnju je porastao za +{razlika} cm. Trenutno: {trenutni_nivo} cm ({vrijeme_mjerenja})."
        )

if __name__ == "__main__":
    main()
