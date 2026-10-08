"""Génère un jeu de données de démonstration d'un parc informatique (données fictives).

Sorties dans data/ : equipements.csv, utilisateurs.csv, mouvements.csv.
Des anomalies sont injectées volontairement (doublons de n° de série, matériel attribué
à des personnes parties, statuts incohérents avec les mouvements, garanties manquantes)
pour être détectées par les contrôles de sql/controles.sql.
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)

SITES = ["Paris La Défense", "Paris Bercy", "Lyon", "Marseille", "Nantes", "Lille"]
SERVICES = ["Agence", "Back-office", "Risques", "Conformité", "IT", "RH", "Marchés"]
PRENOMS = ["Camille", "Lucas", "Inès", "Hugo", "Léa", "Nathan", "Sarah", "Yanis", "Chloé", "Adam",
           "Manon", "Karim", "Emma", "Mehdi", "Julie", "Thomas", "Amina", "Louis", "Clara", "Rayan"]
NOMS = ["Martin", "Bernard", "Dubois", "Moreau", "Laurent", "Simon", "Michel", "Garcia", "Benali",
        "Roux", "Fournier", "Girard", "Bonnet", "Mercier", "Haddad", "Lambert", "Fontaine", "Chevalier"]
TYPES = {  # type: (modèles, durée de vie en années, part du parc)
    "PC portable": (["Dell Latitude 5440", "HP EliteBook 840 G10", "Lenovo ThinkPad T14"], 4, 0.45),
    "PC fixe": (["Dell OptiPlex 7010", "HP EliteDesk 800 G9"], 5, 0.12),
    "Écran": (["Dell P2423", "HP E24 G5", "Iiyama XUB2492"], 6, 0.28),
    "Smartphone": (["iPhone 13", "Samsung Galaxy A54"], 3, 0.15),
}
TODAY = date(2026, 10, 1)


def rand_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))


# ---- utilisateurs
users = []
for i in range(1, 2201):
    actif = random.random() > 0.08
    users.append({
        "matricule": f"U{i:05d}",
        "nom": f"{random.choice(PRENOMS)} {random.choice(NOMS)}",
        "service": random.choice(SERVICES),
        "site": random.choice(SITES),
        "statut": "actif" if actif else "parti",
        "date_depart": "" if actif else rand_date(date(2025, 1, 1), TODAY).isoformat(),
    })
actifs = [u for u in users if u["statut"] == "actif"]
partis = [u for u in users if u["statut"] == "parti"]

# ---- équipements + mouvements
equipements, mouvements = [], []
n_mvt = 0


def mvt(asset, d, typ, user="", site=""):
    global n_mvt
    n_mvt += 1
    mouvements.append({"id_mouvement": f"M{n_mvt:06d}", "id_equipement": asset, "date": d.isoformat(),
                       "type": typ, "matricule": user, "site": site})


for i in range(1, 5001):
    typ = random.choices(list(TYPES), weights=[v[2] for v in TYPES.values()])[0]
    modeles, vie, _ = TYPES[typ]
    achat = rand_date(date(2019, 1, 1), date(2026, 6, 30))
    aid = f"EQ{i:05d}"
    site = random.choice(SITES)
    eq = {"id_equipement": aid, "numero_serie": f"SN{random.randint(10**8, 10**9 - 1)}", "type": typ,
          "modele": random.choice(modeles), "date_achat": achat.isoformat(),
          "fin_garantie": (achat + timedelta(days=365 * 3)).isoformat(), "cout_achat": "",
          "site": site, "statut": "", "matricule": ""}
    eq["cout_achat"] = {"PC portable": 1150, "PC fixe": 850, "Écran": 210, "Smartphone": 480}[typ]
    mvt(aid, achat, "entrée stock", site=site)
    d = achat + timedelta(days=random.randint(2, 30))
    statut, holder = "en stock", ""
    while d < TODAY:
        if statut == "en stock" and random.random() < 0.85:
            holder = random.choice(actifs)["matricule"]
            mvt(aid, d, "attribution", holder, site)
            statut = "attribué"
            d += timedelta(days=random.randint(200, 1100))
        elif statut == "attribué":
            mvt(aid, d, "restitution", holder, site)
            statut, holder = "en stock", ""
            d += timedelta(days=random.randint(5, 90))
        else:
            break
    if (TODAY - achat).days > 365 * vie and random.random() < 0.5 and statut == "en stock":
        mvt(aid, TODAY - timedelta(days=random.randint(1, 120)), "mise au rebut", site=site)
        statut = "réformé"
    eq["statut"], eq["matricule"] = statut, holder
    equipements.append(eq)

# ---- anomalies injectées (environ 3 % du parc)
sample = random.sample(equipements, 160)
for k, eq in enumerate(sample):
    kind = k % 5
    if kind == 0:  # doublon de numéro de série
        eq["numero_serie"] = random.choice(equipements)["numero_serie"]
    elif kind == 1 and eq["statut"] == "attribué":  # attribué à une personne partie
        eq["matricule"] = random.choice(partis)["matricule"]
    elif kind == 2:  # statut base ≠ dernier mouvement
        eq["statut"] = "en stock" if eq["statut"] == "attribué" else "attribué"
    elif kind == 3:  # garantie manquante
        eq["fin_garantie"] = ""
    elif kind == 4:  # attribué sans utilisateur
        eq["statut"], eq["matricule"] = "attribué", ""

for name, rows in [("utilisateurs", users), ("equipements", equipements), ("mouvements", mouvements)]:
    with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"{name}: {len(rows)} lignes")
