import os
import sys
import json
import numpy as np
from PIL import Image


SIL_DIR = r"C:\Users\Tirocinio\Desktop\Yolo_Project\progetto_con_lllm\progetto_llm_con_montaggio\silhouettes"


def load_meta():
    path = os.path.join(SIL_DIR, "silhouettes_meta.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"parts": {}}


def save_meta(meta):
    path = os.path.join(SIL_DIR, "silhouettes_meta.json")
    with open(path, "w") as f:
        json.dump(meta, f, indent=2)


def rotate_png(code, degrees):

    png_path = os.path.join(SIL_DIR, f"{code}.png")
    if not os.path.exists(png_path):
        print(f"  ERRORE: {png_path} non trovato.")

        disponibili = [f[:-4] for f in os.listdir(SIL_DIR) if f.lower().endswith(".png")]
        print(f"  Pezzi disponibili: {', '.join(sorted(disponibili))}")
        return False

    img = Image.open(png_path).convert("RGBA")

    deg = degrees % 360
    if deg == 0:
        print("  0 gradi: nessuna modifica.")
        return True


    if deg in (90, 180, 270):
        arr = np.array(img)
        k = deg // 90
        arr = np.rot90(arr, k)
        out = Image.fromarray(arr, mode="RGBA")
    else:

        out = img.rotate(deg, expand=True, resample=Image.BICUBIC)

    out.save(png_path)


    meta = load_meta()
    if code in meta.get("parts", {}):
        info = meta["parts"][code]
        info["img_wh"] = [out.width, out.height]
        if deg in (90, 270) and "size_mm" in info:
            info["size_mm"] = [info["size_mm"][1], info["size_mm"][0]]
        save_meta(meta)

    print(f"  OK: {code} ruotato di {deg} gradi. Nuova dimensione {out.width}x{out.height}px.")
    return True


def main():
    print(f"Cartella silhouette: {SIL_DIR}")
    if not os.path.isdir(SIL_DIR):
        print("ERRORE: la cartella delle silhouette non esiste. "
              "Controlla il percorso SIL_DIR in cima allo script.")
        return


    if len(sys.argv) == 3:
        code = sys.argv[1].strip().upper()
        try:
            deg = float(sys.argv[2])
        except ValueError:
            print("Il secondo argomento deve essere un numero di gradi.")
            return
        rotate_png(code, deg)
        return


    print("\nModalita' interattiva. Scrivi 'fine' come nome pezzo per uscire.\n")
    while True:
        code = input("Nome del pezzo (es. A077): ").strip().upper()
        if code in ("FINE", "EXIT", "Q", ""):
            print("Uscita.")
            break
        try:
            deg = float(input("Di quanti gradi ruotarlo? (es. 180): ").strip())
        except ValueError:
            print("  Devi inserire un numero. Riprova.\n")
            continue
        rotate_png(code, deg)
        print()


if __name__ == "__main__":
    main()
