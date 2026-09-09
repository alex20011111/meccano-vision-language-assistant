import os
import sys
import json
import numpy as np

try:
    import trimesh
    from shapely.geometry import Polygon, MultiPolygon
    from shapely.ops import unary_union
    from PIL import Image, ImageDraw
except ImportError:
    print("Mancano librerie. Esegui:  pip install trimesh numpy pillow shapely")
    sys.exit(1)


STL_DIR = r"C:\Users\Tirocinio\Desktop\Yolo_Project\progetto_con_lllm\progetto_llm_con_montaggio\stl"
OUT_DIR = r"C:\Users\Tirocinio\Desktop\Yolo_Project\progetto_con_lllm\progetto_llm_con_montaggio\silhouettes"
PPMM = 4.0


def rot_matrix(ax, ay, az):

    rx, ry, rz = np.radians([ax, ay, az])
    Rx = np.array([[1, 0, 0, 0],
                   [0, np.cos(rx), -np.sin(rx), 0],
                   [0, np.sin(rx), np.cos(rx), 0],
                   [0, 0, 0, 1]])
    Ry = np.array([[np.cos(ry), 0, np.sin(ry), 0],
                   [0, 1, 0, 0],
                   [-np.sin(ry), 0, np.cos(ry), 0],
                   [0, 0, 0, 1]])
    Rz = np.array([[np.cos(rz), -np.sin(rz), 0, 0],
                   [np.sin(rz), np.cos(rz), 0, 0],
                   [0, 0, 1, 0],
                   [0, 0, 0, 1]])
    return Rz @ Ry @ Rx


def mesh_outline_polygon(mesh, min_tri_area=1e-9):

    verts = mesh.vertices[:, :2]
    faces = mesh.faces
    tri_polys = []
    for f in faces:
        p = verts[f]
        a = p[1] - p[0]; b = p[2] - p[0]
        area = 0.5 * abs(a[0] * b[1] - a[1] * b[0])
        if area < min_tri_area:
            continue
        try:
            tri_polys.append(Polygon(p))
        except Exception:
            continue
    if not tri_polys:
        return None
    merged = unary_union(tri_polys)

    def fill_holes(poly):
        if poly.geom_type == "Polygon":
            return Polygon(poly.exterior)
        elif poly.geom_type == "MultiPolygon":
            return MultiPolygon([Polygon(g.exterior) for g in poly.geoms])
        return poly
    return fill_holes(merged)


def rasterize_polygon(poly, ppmm, pad_px=6):
    minx, miny, maxx, maxy = poly.bounds
    size_mm = (maxx - minx, maxy - miny)
    W = int(np.ceil(size_mm[0] * ppmm)) + 2 * pad_px
    H = int(np.ceil(size_mm[1] * ppmm)) + 2 * pad_px
    W = max(W, 1); H = max(H, 1)
    img = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(img)

    def to_px(coords):
        return [((x - minx) * ppmm + pad_px, (y - miny) * ppmm + pad_px)
                for (x, y) in coords]
    geoms = poly.geoms if poly.geom_type == "MultiPolygon" else [poly]
    for g in geoms:
        draw.polygon(to_px(list(g.exterior.coords)), fill=255)
    mask = np.array(img, dtype=np.uint8)
    mask = np.flipud(mask)
    return mask, (1.0 / ppmm), size_mm


def mask_to_rgba(mask):
    H, W = mask.shape
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = mask
    return Image.fromarray(rgba, mode="RGBA")


def generate_one(stl_path, ax, ay, az, ppmm):

    mesh = trimesh.load(stl_path, force="mesh")
    if mesh.is_empty:
        return None, None, None
    if (ax, ay, az) != (0, 0, 0):
        mesh.apply_transform(rot_matrix(ax, ay, az))
    poly = mesh_outline_polygon(mesh)
    if poly is None or poly.is_empty:
        return None, None, None
    mask, mm_per_px, size_mm = rasterize_polygon(poly, ppmm)
    return mask, mm_per_px, size_mm


def load_meta():
    path = os.path.join(OUT_DIR, "silhouettes_meta.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"ppmm": PPMM, "parts": {}}


def save_meta(meta):
    with open(os.path.join(OUT_DIR, "silhouettes_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if not os.path.isdir(STL_DIR):
        print(f"ERRORE: cartella STL non trovata: {STL_DIR}")
        return

    stl_files = sorted(f for f in os.listdir(STL_DIR) if f.lower().endswith(".stl"))
    if not stl_files:
        print(f"Nessun .stl in {STL_DIR}")
        return

    meta = load_meta()
    print(f"Trovati {len(stl_files)} pezzi.\n")
    print("Per ogni pezzo: genero la silhouette, tu guardi la PNG nella cartella")
    print(f"  {OUT_DIR}")
    print("e decidi se va bene o come ruotarla nello spazio 3D.\n")
    print("ASSI: X=inclina avanti/indietro, Y=inclina di lato, Z=gira piatto")
    print("Per una ruota vista di taglio prova X=90 oppure Y=90.\n")

    for fname in stl_files:
        code = os.path.splitext(fname)[0]
        stl_path = os.path.join(STL_DIR, fname)
        ax = ay = az = 0.0

        while True:
            mask, mm_per_px, size_mm = generate_one(stl_path, ax, ay, az, PPMM)
            if mask is None:
                print(f"[{code}] impossibile generare, salto.")
                break

            img = mask_to_rgba(mask)
            png_path = os.path.join(OUT_DIR, f"{code}.png")
            img.save(png_path)


            frac = (mask > 0).sum() / mask.size
            print(f"[{code}] generato con rotazione X={ax:.0f} Y={ay:.0f} Z={az:.0f}")
            print(f"        dimensione {img.width}x{img.height}px, "
                  f"pezzo ~{size_mm[0]:.1f}x{size_mm[1]:.1f}mm, riempimento {frac:.0%}")
            print(f"        --> GUARDA il file {code}.png nella cartella silhouette")

            scelta = input("        [Invio]=ok  |  X Y Z (gradi) per ruotare  |  's'=salta: ").strip()

            if scelta.lower() in ("s", "skip", "salta"):
                print("        saltato.\n")
                break
            if scelta == "":

                meta.setdefault("parts", {})[code] = {
                    "png": f"{code}.png",
                    "mm_per_px": mm_per_px,
                    "size_mm": [float(size_mm[0]), float(size_mm[1])],
                    "img_wh": [img.width, img.height],
                }
                save_meta(meta)
                print(f"        OK, {code} confermato.\n")
                break

            parts = scelta.replace(",", " ").split()
            try:
                vals = [float(x) for x in parts]
                if len(vals) == 1:
                    ax, ay, az = vals[0], 0, 0
                elif len(vals) == 2:
                    ax, ay, az = vals[0], vals[1], 0
                elif len(vals) >= 3:
                    ax, ay, az = vals[0], vals[1], vals[2]
                print(f"        rigenero con X={ax} Y={ay} Z={az} ...")
            except ValueError:
                print("        input non valido. Scrivi tre numeri (es. 90 0 0) "
                      "oppure Invio per confermare.\n")

    print("Finito. Silhouette in:", OUT_DIR)


if __name__ == "__main__":
    main()
