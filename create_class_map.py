import json
import os
import re


MODELLO = r"C:\Users\Tirocinio\Desktop\Yolo_Project\runs\detect\runs_meccano\yolo11l_meccano\weights\best.pt"
STL_DIR = r"C:\Users\Tirocinio\Desktop\Modelli_CAD\File_stl"


OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mappa_classi.json")

PAROLE_MANO = ("hand", "mano", "palm")


def leggi_nomi(path):

    try:
        from ultralytics import YOLO
        names = YOLO(path).names
    except Exception as e:
        print(f"  (ultralytics could not load the model: {e})")
        print('  Trying to read the checkpoint directly...')
        import torch
        ck = torch.load(path, map_location="cpu", weights_only=False)
        names = ck["model"].names
    return [names[i] for i in sorted(names)]


def abbina(stem, classi):

    su = stem.upper()
    for c in classi:
        if su == c.upper():
            return c

    candidati = [c for c in classi
                 if re.match(rf"^{re.escape(c.upper())}[_\-\s]", su)]
    return max(candidati, key=len) if candidati else None


COLORI_RGB = {
    'red':  [0.70, 0.08, 0.08],
    'grey': [0.16, 0.16, 0.17],
    'white': [0.90, 0.90, 0.88],
    'black':   [0.05, 0.05, 0.06],
    'yellow': [0.95, 0.70, 0.05],
    'blue':    [0.10, 0.25, 0.70],
    'green':  [0.10, 0.45, 0.15],
}


def leggi_colori(classi):


    try:
        from parts_catalog import PARTS_CATALOG
    except ImportError:
        print('\n  parts_catalog.py not found: empty colour section.')
        print('  Fill it in to specify colours for each class.')
        return {}

    colori = {}
    for classe in classi:
        voce = PARTS_CATALOG.get(classe)
        if not voce:
            continue

        testo = voce.get("colore", "").lower()
        trovati = [nome for nome in COLORI_RGB if nome in testo]
        if trovati:
            colori[classe] = [COLORI_RGB[n] for n in trovati]
    return colori


def main():
    if not os.path.exists(MODELLO):
        raise SystemExit(f"Model not found:\n  {MODELLO}")
    if not os.path.isdir(STL_DIR):
        raise SystemExit(f"STL folder not found:\n  {STL_DIR}")

    print(f"Reading classes from:\n  {MODELLO}\n")
    nomi = leggi_nomi(MODELLO)

    print(f"{len(nomi)} classes in model order:")
    for i, n in enumerate(nomi):
        print(f"  {i:>2}: {n}")

    stl_files = sorted(f for f in os.listdir(STL_DIR) if f.lower().endswith(".stl"))
    print(f"\n{len(stl_files)} STL files in:\n  {STL_DIR}\n")

    mappa_stl, cfg_mano, orfani = {}, None, []

    for f in stl_files:
        stem = os.path.splitext(f)[0]
        if any(p in stem.lower() for p in PAROLE_MANO):
            if cfg_mano is None:
                classe_mano = next(
                    (n for n in nomi if any(p in n.lower() for p in PAROLE_MANO)), None
                )
                if classe_mano:
                    cfg_mano = {"file": f, "classe": classe_mano}
                    continue
        classe = abbina(stem, nomi)
        if classe:
            mappa_stl[f] = classe
        else:
            orfani.append(f)

    colori = leggi_colori(nomi)

    uscita = {"nomi_ordinati": nomi, "stl": mappa_stl}
    if cfg_mano:
        uscita["mano"] = cfg_mano
    if colori:
        uscita["colori"] = colori

    with open(OUT, "w", encoding="utf-8") as fp:
        json.dump(uscita, fp, indent=2, ensure_ascii=False)


    print("=" * 62)
    print('MATCHES')
    for f, c in sorted(mappa_stl.items(), key=lambda kv: kv[1]):
        segno = "=" if os.path.splitext(f)[0].upper() == c.upper() else "~"
        print(f"  {f:<26} {segno}> {c}")
    if cfg_mano:
        print(f"  {cfg_mano['file']:<26} => {cfg_mano['classe']}  (hand section)")

    doppie = {}
    for f, c in mappa_stl.items():
        doppie.setdefault(c, []).append(f)
    multi = {c: fs for c, fs in doppie.items() if len(fs) > 1}
    if multi:
        print('\nCLASSES WITH MULTIPLE STL FILES:')
        for c, fs in multi.items():
            print(f"  {c}: {', '.join(fs)}")

    coperte = set(mappa_stl.values()) | ({cfg_mano["classe"]} if cfg_mano else set())

    if colori:
        nomi_rgb = {tuple(v): k for k, v in COLORI_RGB.items()}
        print('\nCOLOURS (from parts_catalog.py):')
        for c in nomi:
            if c in colori:
                elenco = ", ".join(nomi_rgb.get(tuple(rgb), "?") for rgb in colori[c])
                print(f"  {c:<8} {elenco}")
        senza = [c for c in nomi if c not in colori and c in coperte]
        if senza:
            print(f"  missing colour: {', '.join(senza)} -> will use the random palette")

    scoperte = [n for n in nomi if n not in coperte]
    if scoperte:
        print(f"\nCLASSES WITHOUT STL ({len(scoperte)}):")
        print(f"  {', '.join(scoperte)}")
        print('  These classes will not appear in synthetic scenes. For incorrect filenames,')
        print('  rename the STL; parts without CAD must come from real images.')

    if orfani:
        print(f"\nUNMATCHED STLS ({len(orfani)}):")
        for f in orfani:
            print(f"  {f}")
        print('  For class variants, use CLASS_variant.stl')
        print('  (e.g. A632_red.stl) and run again.')

    print("\n" + "=" * 62)
    print('OUTPUT FILE:')
    print(f"  {OUT}")
    if scoperte or orfani:
        print('\nResolve the issues above and run again, or edit the JSON manually.')
    else:
        print('\nAll files matched. The dataset can be generated.')

    print('\nArgument for generate_meccano_dataset.py:')
    print(f"  --stl_dir {STL_DIR}")


if __name__ == "__main__":
    main()
