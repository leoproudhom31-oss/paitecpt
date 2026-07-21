# paitecpt

Corpus de texte **100 % en langue paite** (kuki-chin, Manipur / Chin Hills),
destiné au *continued pre-training* d'un modèle de langue pour cette langue
peu dotée. Le corpus est construit à partir de sources paites authentiques
(Bible, recueils de chants et de littérature traditionnelle), nettoyées pour
ne conserver **que du texte paite** — sans chiffres, sans étiquettes, sans
tokens anglais/hindi.

## Le dataset

Fichier : [`data/processed/dataset_paite.jsonl`](data/processed/dataset_paite.jsonl)
Format : une ligne JSON par entrée, `{"text": "..."}` (80–300 mots de prose
ou de poésie paite).

| Source | Entrées | Mots | Nature | Extraction |
|---|---:|---:|---|---|
| Bible paite (Pathian Laisiangthou) | 1009 | 261 092 | Prose | texte + nettoyage |
| Paite La Gousiah (1960) | 46 | 7 607 | Chants + récits | OCR visuel manuel |
| Paite Sintute Tehna (1960) | 120 | 21 707 | Chants + biographies | OCR (tesseract) |
| Paite Late leh Thute | 109 | 22 215 | Chants + dictons | OCR (tesseract) |
| **Total** | **1284** | **312 621** | | |

Vocabulaire : **~23 740 formes uniques**.
Garanties de propreté : **0 chiffre**, 0 étiquette de source, 0 sigle
anglais, 0 token tout-en-capitales résiduel (seuls subsistent les guillemets
courbes des dialogues paites).

## Ce qui a été ajouté (synthèse)

À partir du corpus biblique initial (1009 entrées), le dataset a été enrichi
puis nettoyé en profondeur :

1. **Paite La Gousiah (1960)** — 46 entrées.
   Recueil de chants traditionnels et de récits (Khupching La, Liandou La,
   Jawl La, …) transcrits **visuellement page par page** depuis le PDF scanné,
   puis découpés. C'est la portion de meilleure qualité (transcription
   manuelle, quasi sans bruit).

2. **Nettoyage « 100 % paite » de tout le dataset.**
   - Suppression de **~24 000 chiffres** : numéros de versets collés aux mots
     (`2Lei`, `26Pathian`) et nombres isolés.
   - Suppression des **préfixes de source** (`GENESIS 24:`,
     `PAITE LA GOUSIAH - JAWL LA:`) qui contenaient des noms de livres
     anglais + numéros de chapitre.
   - Suppression des tokens non-paites : sigles pointés (`A.D.`, `U.N.`,
     `U.S.A.`, `P.N.C.`, `I.A.S.`) et mots éditoriaux anglais.
   - Vérification anti-faux-positifs : les mots qui *ressemblent* à de
     l'anglais mais sont bien paites ont été conservés (`that` = tuer,
     `long` = bateau, `man` = attraper, `them` = quelques).

3. **Paite Sintute Tehna (1960)** — 120 entrées, et
   **Paite Late leh Thute** — 109 entrées.
   Extraits par **OCR** (tesseract, alphabet latin — le paite s'écrit en
   alphabet latin) des PDF scannés, puis nettoyés :
   - suppression des en-têtes de page, numéros de page, marqueurs de strophe
     (chiffres arabes, chiffres romains, `(a)`/`(b)`) ;
   - suppression du bruit OCR (symboles parasites, tokens sans voyelle,
     tokens camelCase, jetons tout-en-capitales) via une **jauge de
     plausibilité paite** calibrée sur du texte paite connu (fraction de mots
     ≥ 3 lettres et fraction de mots avec voyelle) ;
   - suppression des mots anglais / hindi restants ;
   - **déduplication** par 4-grammes normalisés (repli des variantes OCR
     `Geeltui`↔`Geltui`) contre le corpus existant.
   Résultat : contenu **99,8 % nouveau** (0,2 % de 4-grammes en commun),
   apportant **~7 500 nouvelles formes** de vocabulaire.

> Note qualité : les portions Bible et La Gousiah sont (quasi) sans bruit.
> Les portions Sintute Tehna et Late leh Thute proviennent d'un OCR de scans
> anciens (années 1960) ; malgré un nettoyage agressif, il subsiste des
> erreurs OCR résiduelles (lettres mal reconnues, voyelles dédoublées) qui ne
> peuvent être corrigées automatiquement faute de correcteur orthographique
> paite.

## Pipeline / scripts

Tous les scripts sont dans [`scripts/`](scripts/) :

| Script | Rôle |
|---|---|
| `clean_and_chunk.py` | Nettoie et découpe le texte biblique brut en JSONL. |
| `process_la_gousiah.py` | Intègre le texte transcrit de *La Gousiah*. |
| `ocr_pdf.sh` | OCR page par page d'un PDF scanné (tesseract, 200 dpi, timeout par page, image supprimée aussitôt pour économiser le disque). |
| `process_ocr_books.py` | Nettoyage « 100 % paite », déduplication 4-grammes et intégration des livres OCR. |
| `clean_dataset.py` | Passe de nettoyage finale (chiffres, préfixes, tokens non-paites) sur tout le dataset. |

### Reproduire

```bash
# 1. OCR d'un PDF scanné  ->  texte brut
bash scripts/ocr_pdf.sh "BVP-PLT-PAITE-SINTUTE-TEHNA-V-1960.pdf" data/raw/sintute_tehna_raw.txt 200 45

# 2. Nettoyage + dedup + integration au dataset
OCR_SCRATCH=data/raw python scripts/process_ocr_books.py
```

## Sources

Ouvrages paites numérisés par la **Paite Literature Society** (Churachandpur,
Manipur) et publications associées. Les PDF sources sont volumineux et suivis
séparément (non embarqués dans cette branche).
