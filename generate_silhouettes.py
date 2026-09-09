import os
import sys
import json
import argparse
import numpy as np

try:
    import trimesh
    from shapely.geometry import Polygon, MultiPolygon
    from shapely.ops import unary_union
    from PIL import Image, ImageDraw
except ImportError:
    print("Mancano librerie:  pip install trimesh numpy pillow shapely scipy")
    sys.exit(1)


def auto_flatten(mesh):


    m = mesh.copy()
    v = m.vertices - m.vertices.mean(axis=0)


    cov = np.cov(v.T)
    eigvals, eigvecs = np.linalg.eigh(cov)


    thickness_dir = eigvecs[:, 0]
    mid_dir       = eigvecs[:, 1]
    long_dir      = eigvecs[:, 2]


    R = np.eye(4)
    basis = np.column_stack([long_dir, mid_dir, thickness_dir])

    R[:3, :3] = basis.T
    m.apply_transform(R)
    return m


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--ppmm", type=float, default=4.0)
    ap.add_argument("--no-auto", action="store_true",
                    help="disattiva orientamento automatico")
    args = ap.parse_args()

    os.makedirs(args.output, exist_ok=True)
    meta = {"ppmm": args.ppmm, "parts": {}}

    stl_files = sorted(f for f in os.listdir(args.input) if f.lower().endswith(".stl"))
    if not stl_files:
        print(f"Nessun .stl in {args.input}")
        return

    for fname in stl_files:
        code = os.path.splitext(fname)[0]
        path = os.path.join(args.input, fname)
        print(f"[{code}] {fname} ...")

        mesh = trimesh.load(path, force="mesh")
        if mesh.is_empty:
            print("  mesh vuota, salto.")
            continue


        if not args.no_auto:
            try:
                mesh = auto_flatten(mesh)
            except Exception as e:
                print(f"  auto-orient fallito ({e}), uso orientamento originale.")

        poly = mesh_outline_polygon(mesh)
        if poly is None or poly.is_empty:
            print("  impossibile estrarre sagoma, salto.")
            continue

        mask, mm_per_px, size_mm = rasterize_polygon(poly, args.ppmm)
        img = mask_to_rgba(mask)
        img.save(os.path.join(args.output, f"{code}.png"))

        frac = (mask > 0).sum() / mask.size
        meta["parts"][code] = {
            "png": f"{code}.png",
            "mm_per_px": mm_per_px,
            "size_mm": [float(size_mm[0]), float(size_mm[1])],
            "img_wh": [img.width, img.height],
        }
        print(f"  OK  {img.width}x{img.height}px  pezzo ~{size_mm[0]:.1f}x{size_mm[1]:.1f}mm  "
              f"riempimento {frac:.0%}")

    with open(os.path.join(args.output, "silhouettes_meta.json"), "w") as fp:
        json.dump(meta, fp, indent=2)
    print(f"\nGenerate {len(meta['parts'])} silhouette in {args.output}")


if __name__ == "__main__":
    main()
