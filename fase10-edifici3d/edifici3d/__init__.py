"""EuGEnio – edifici 3D (fase 10, Fase A del programma: edificio e contesto in Emilia-Romagna).

Moduli:
  modello   corpo ed edificio (§ 7 della proposta), stima di piani e superfici (§ 8), indicatori geometrici (§ 9, analisi 1)
  fonti     fonti nei TOML, scaricamento e archivi separati per licenza (CC BY / ODbL)
  uvl       DBTR – Unità volumetriche: lettura del GeoPackage e controllo degli attributi (gronda/colmo, piani)
  osm       edifici OpenStreetMap (archivio ODbL separato)
  dtm       DTM: Cloud Optimized GeoTIFF, tessere del terreno (Terrarium) e quota del terreno per corpo
  tessere   PMTiles vettoriali dei corpi (uno per licenza)
  sintetico quartiere e DTM sintetici per prove e dimostrazioni (dichiarati come tali)
  ortofoto_sito  ortofoto AGEA scaricate a mano per un sito: 50 cm, COG e PMTiles (Fase B)
  lidar     DSM ridotto (1 m, int16 in decimetri) e falde dei tetti per corpo da DSM o LAS (Fase C)
  pipeline  pipeline notturna a tessere, una zona per TOML (zone/*.toml): riprendibile, idempotente, con limiti (Fase C)
  campione  rilievo LiDAR sintetico per prove e demo (Fase C)
  importa   modelli DXF e IFC dell'utente → corpi, altezze e falde (GeoJSON «eugenio-modello-1»), file non fidati (Fase C)
  regioni   fonti per regione (fonti/regioni.toml): controllo delle regole, riepilogo, prova dal vivo (Fase E)
  zornade   altezze di Zornade da un estratto consegnato → archivio ODbL separato, confronto con le altezze CC BY (Fase E)
  analisi   aggancio facoltativo al modulo privato delle analisi 5 e 7–13 (Fase E)

Le fonti delle ortofoto servite dal proxy del server stanno in `ortofoto/*.toml` (una per regione), lette da
fase4-server/servizio/ortofoto.py.

Codice AGPL-3.0. Nessun testo, prospetto o coefficiente delle norme UNI: le metodiche UNI stanno nel modulo privato
`uni_privato/` (fuori dal repository), che `analisi` carica solo se c'è; senza, le analisi 5 e 7–13 risultano «non
disponibili in questa installazione».
"""
__version__ = "0.4.0"
