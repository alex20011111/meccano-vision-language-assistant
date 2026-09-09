import blenderproc as bproc


import argparse

import numpy as np

p = argparse.ArgumentParser()
p.add_argument("--hdri_dir", required=True)
p.add_argument("--colori", nargs="+", default=["0.28,0.28,0.29"],
               help="lista di colori r,g,b (0-1) separati da spazio")
p.add_argument("--out", default="prova_colori.png")
p.add_argument("--roughness", type=float, default=0.5,
               help="stessa rugosita' del generatore (plastica opaca)")
args = p.parse_args()

import glob
import os

colori = []
for c in args.colori:
    parts = [float(x) for x in c.replace(";", ",").split(",")]
    if len(parts) == 3:
        colori.append(parts)

hdris = [f for f in glob.glob(os.path.join(args.hdri_dir, "**", "*"), recursive=True)
         if f.lower().endswith((".hdr", ".exr"))]
if not hdris:
    raise SystemExit(f"Nessun HDRI in {args.hdri_dir}")

bproc.init()
bproc.world.set_world_background_hdr_img(hdris[0], strength=1.0)


bproc.camera.set_resolution(300 * max(1, len(colori)), 360)
cam_pose = bproc.math.build_transformation_mat([0, 0, 1.2], [0, 0, 0])
bproc.camera.add_camera_pose(cam_pose)


passo = 0.25
x0 = -(len(colori) - 1) * passo / 2
for i, rgb in enumerate(colori):
    s = bproc.object.create_primitive("SPHERE")
    s.set_scale([0.09] * 3)
    s.set_location([x0 + i * passo, 0, 0])
    s.set_shading_mode("smooth")
    mat = s.new_material(f"c{i}")
    mat.set_principled_shader_value("Base Color", [*rgb, 1.0])
    mat.set_principled_shader_value("Metallic", 0.0)
    mat.set_principled_shader_value("Roughness", args.roughness)

bproc.renderer.set_max_amount_of_samples(64)
bproc.renderer.set_output_format(enable_transparency=False)
data = bproc.renderer.render()


img = data["colors"][0]
try:
    import imageio
    imageio.imwrite(args.out, np.asarray(img).astype(np.uint8))
except Exception:
    from PIL import Image
    Image.fromarray(np.asarray(img).astype(np.uint8)).save(args.out)

print(f"\nSalvata anteprima in {os.path.abspath(args.out)}")
print("Colori mostrati (da sinistra a destra):")
for rgb in colori:
    print(f"  {rgb[0]:.2f}, {rgb[1]:.2f}, {rgb[2]:.2f}")
print("\nQuando trovi il grigio giusto, mettilo in crea_mappa.py alla voce "
      "\"grigio\" e rigenera la mappa.")
