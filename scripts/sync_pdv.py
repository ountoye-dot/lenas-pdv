#!/usr/bin/env python3
"""Synchronise les points de vente de lenas.be vers data/points-de-vente.json.

- Lit la section « Verkooppunten » (tableau) de https://www.lenas.be/
- Géocode les adresses avec Nominatim (OpenStreetMap), uniquement les nouvelles adresses
- N'écrase JAMAIS le fichier si la lecture semble anormale (moins de MIN_POINTS lignes)
"""
import datetime
import json
import pathlib
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

SOURCE = "https://www.lenas.be/"
OUT = pathlib.Path("data/points-de-vente.json")
CONTACT = "VOTRE_EMAIL"  # <-- à remplacer par votre e-mail (exigé par la politique d'usage de Nominatim)
UA = f"LenasPointsDeVenteSync/1.0 ({CONTACT})"
MIN_POINTS = 10


def fetch_html():
    r = requests.get(SOURCE, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return r.text


def clean_url(url):
    url = re.sub(r"[?&]fbclid=[^&]*", "", url or "")
    return url.rstrip("?&")


def split_address(raw):
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    parts = [p for p in parts if p.lower() not in ("belgië", "belgique", "belgium")]
    street, postal, city = "", "", ""
    for i, p in enumerate(parts):
        m = re.match(r"^(\d{4})\s+(.+)$", p)
        if m:
            postal, city = m.group(1), m.group(2)
            street = ", ".join(parts[:i])
            break
    if not postal:
        street = ", ".join(parts)
    return street, postal, city


def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for tr in soup.select("table tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        a = tds[0].find("a")
        name = (a or tds[0]).get_text(" ", strip=True)
        website = clean_url(a["href"]) if a and a.has_attr("href") else ""
        street, postal, city = split_address(tds[1].get_text(" ", strip=True))
        if name and (street or postal):
            rows.append({"name": name, "address": street, "postal": postal, "city": city, "website": website})
    return rows


def geocode(query):
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "be"},
        headers={"User-Agent": UA},
        timeout=30,
    )
    r.raise_for_status()
    time.sleep(1.1)  # max 1 requête / seconde
    data = r.json()
    return (float(data[0]["lat"]), float(data[0]["lon"])) if data else None


def main():
    previous = {"points": []}
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            pass
    cache = {(p["address"], p["postal"], p["city"]): p for p in previous.get("points", [])}

    rows = parse(fetch_html())
    if len(rows) < MIN_POINTS:
        print(f"ERREUR : seulement {len(rows)} lignes lues sur lenas.be, fichier conservé.")
        sys.exit(1)

    points = []
    for row in rows:
        key = (row["address"], row["postal"], row["city"])
        old = cache.get(key)
        lat = lng = None
        approx = False
        if old and old.get("lat") is not None:
            lat, lng, approx = old["lat"], old["lng"], old.get("approx", False)
        else:
            try:
                hit = geocode(f'{row["address"]}, {row["postal"]} {row["city"]}, Belgium')
                if not hit:
                    hit = geocode(f'{row["postal"]} {row["city"]}, Belgium')
                    approx = True
                if hit:
                    lat, lng = hit
            except Exception as e:
                print(f"Géocodage impossible pour {row['name']} : {e}")
        points.append({
            "name": row["name"], "type": "Revendeur",
            "address": row["address"], "postal": row["postal"], "city": row["city"],
            "phone": "", "website": row["website"], "hours": "",
            "lat": lat, "lng": lng, "approx": approx,
        })

    if previous.get("points") == points:
        print(f"Aucun changement ({len(points)} points de vente).")
        return
    payload = {
        "source": SOURCE,
        "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "points": points,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(points)} points de vente écrits.")


if __name__ == "__main__":
    main()
