import blenderproc as bproc


import argparse
import glob
import json
import os
import random

import numpy as np


p = argparse.ArgumentParser()
p.add_argument("--stl_dir", default="stl", help="cartella con gli STL")
p.add_argument("--mappa_classi", default="mappa_classi.json",
               help="JSON con nomi_ordinati (= yolo_model.names) e mappa STL->classe")
p.add_argument("--cc_textures", default="assets/cc_textures")
p.add_argument("--sfondi_reali", default=None,
               help="cartella di foto del piano vuoto, da cattura_sfondi.py")
p.add_argument("--prob_sfondo_reale", type=float, default=0.7,
               help="quota di scene che usa una foto vera invece di una texture CC")
p.add_argument("--prob_mano", type=float, default=0.35,
               help="quota di scene in cui compare la mano")
p.add_argument("--prob_colore_random", type=float, default=0.12,
               help="quota di pezzi con colore fuori distribuzione, per non "
                    "far dipendere il modello solo dal colore")
p.add_argument("--hdri_dir", default="assets/haven")
p.add_argument("--output", default="dataset_sintetico")


p.add_argument("--z_min", type=float, default=0.30, help="altezza minima camera [m]")
p.add_argument("--z_max", type=float, default=0.40, help="altezza massima camera [m]")
p.add_argument("--fx", type=float, default=920.0)
p.add_argument("--fy", type=float, default=920.0)
p.add_argument("--cx", type=float, default=640.0)
p.add_argument("--cy", type=float, default=360.0)


p.add_argument("--larghezza", type=int, default=1920)
p.add_argument("--altezza", type=int, default=1080)


p.add_argument("--scene", type=int, default=800, help="numero di simulazioni fisiche")
p.add_argument("--viste_per_scena", type=int, default=4)
p.add_argument("--pezzi_min", type=int, default=4)
p.add_argument("--pezzi_max", type=int, default=22)
p.add_argument("--copie_per_classe", type=int, default=4)
p.add_argument("--area_min_px", type=int, default=250,
               help="scarta le istanze con meno pixel visibili di questo valore. "
                    "A 30-40 cm un dado da 10 mm occupa ~600-1600 px, quindi 250 "
                    "significa 'visibile per meno di un terzo'")


p.add_argument("--scala_cad", type=float, default=0.001, help="0.001 se gli STL sono in mm")
p.add_argument("--scala_mano", type=float, default=None,
               help="scala solo per la mano, se e' in un'unita' diversa dai pezzi. "
                    "Es. 0.01 se la mano e' in cm mentre i pezzi sono in metri. "
                    "Se non dato, usa --scala_cad come gli altri.")
p.add_argument("--qualita", choices=["bassa", "media", "alta"], default="media")
p.add_argument("--frazione_val", type=float, default=0.1)
p.add_argument("--seed", type=int, default=0)
args = p.parse_args()

random.seed(args.seed)
np.random.seed(args.seed)


JITTER_XY = 0.02
JITTER_TILT = np.deg2rad(3.0)
ROLL_LIBERO = True


colori_per_cat = {}


COLORE_PELLE = [0.80, 0.60, 0.50]

CAMPIONI = {"bassa": 24, "media": 64, "alta": 160}[args.qualita]
SOGLIA_RUMORE = {"bassa": 0.10, "media": 0.03, "alta": 0.01}[args.qualita]


import bpy
try:
    bpy.ops.preferences.addon_enable(module="cycles")
except Exception as e:
    print(f"(nota: addon_enable cycles ha risposto: {e})")

bproc.init()

K = np.array([[args.fx, 0, args.cx],
              [0, args.fy, args.cy],
              [0, 0, 1]])
bproc.camera.set_intrinsics_from_K_matrix(
    K, args.larghezza, args.altezza, clip_start=0.05, clip_end=5.0
)


mezza_larghezza = args.z_min * args.cx / args.fx
mezza_altezza = args.z_min * args.cy / args.fy
z_nom = (args.z_min + args.z_max) / 2
mm_per_px_min = 1000.0 * args.z_min / args.fx
mm_per_px_max = 1000.0 * args.z_max / args.fx

print("=" * 68)
print(f"Camera top-down, altezza randomizzata fra {args.z_min:.2f} e {args.z_max:.2f} m")
print(f"Area inquadrata a {args.z_min:.2f} m: "
      f"{2*mezza_larghezza*100:.1f} x {2*mezza_altezza*100:.1f} cm")
print(f"SCALA: da {mm_per_px_min:.3f} a {mm_per_px_max:.3f} mm/pixel")
print(f"  un pezzo da 100 mm occupa {100/mm_per_px_max:.0f}-{100/mm_per_px_min:.0f} px")
print(f"  un dado da  10 mm occupa {10/mm_per_px_max:.0f}-{10/mm_per_px_min:.0f} px")
print("=" * 68)


RAGGIO_X = mezza_larghezza * 0.60
RAGGIO_Y = mezza_altezza * 0.60


def carica_pezzi():


    with open(args.mappa_classi) as f:
        mappa = json.load(f)

    nomi = mappa["nomi_ordinati"]
    stl_map = mappa["stl"]
    classi = {nome: i + 1 for i, nome in enumerate(nomi)}

    senza_stl = [n for n in nomi if n not in set(stl_map.values())]
    if senza_stl:
        print(f"  ATTENZIONE - classi senza STL, verranno solo dai dati reali: "
              f"{', '.join(senza_stl)}")

    pezzi = []
    for file_stl, nome in sorted(stl_map.items()):
        path = os.path.join(args.stl_dir, file_stl)
        if not os.path.exists(path):
            raise SystemExit(f"Manca {path} (citato in {args.mappa_classi})")
        if nome not in classi:
            raise SystemExit(f"'{nome}' non e' in nomi_ordinati")
        cat_id = classi[nome]

        base = bproc.loader.load_obj(path)[0]
        base.set_scale([args.scala_cad] * 3)


        obj = base.blender_obj
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.make_single_user(object=True, obdata=True)


        try:
            base.persist_transformation_into_mesh(location=False, rotation=False,
                                                  scale=True)
        except RuntimeError as e:
            print(f"       (scala non fusa per {file_stl}: {e} - proseguo)")
        base.set_origin(mode="CENTER_OF_VOLUME")
        base.set_shading_mode("auto", 30)

        dim = base.get_bound_box()
        est = np.sort(dim.max(axis=0) - dim.min(axis=0))[::-1] * 1000
        etichetta = os.path.splitext(file_stl)[0]
        print(f"  {etichetta:>16} -> classe {nome:<8} (id {cat_id:>2})  "
              f"{est[0]:6.1f} x {est[1]:5.1f} x {est[2]:5.1f} mm")
        if est[0] < 3.0:
            print("       ^ sospetto: pezzo sotto i 3 mm. Controlla --scala_cad.")

        for c in range(args.copie_per_classe):
            o = base if c == 0 else base.duplicate()
            o.set_cp("category_id", cat_id)
            o.set_name(f"{etichetta}__{c}")
            o.hide(True)
            pezzi.append(o)

    return pezzi, classi


print("\nCarico i pezzi (controlla che gli ingombri siano quelli veri):")
pezzi, classi = carica_pezzi()

with open(args.mappa_classi) as f:
    _colori_json = json.load(f).get("colori", {})

colori_per_cat = {int(classi[n]): v for n, v in _colori_json.items() if n in classi}


_classi_senza_colore_note = {
    int(cid) for nome, cid in classi.items() if nome not in _colori_json
}

if colori_per_cat:
    print(f"\nColori per classe ({len(colori_per_cat)} definiti):")
    _rev = {v: k for k, v in classi.items()}
    for cid in sorted(colori_per_cat):
        n_col = len(colori_per_cat[cid])
        print(f"  {_rev.get(cid, cid):<8} {n_col} colore/i")
else:
    print("\nNessuna sezione 'colori' nella mappa: tutti i pezzi avranno "
          "colore casuale.\n  Il colore e' un discriminatore forte, valuta di "
          "compilarla.")

os.makedirs(args.output, exist_ok=True)
with open(os.path.join(args.output, "classi.json"), "w") as f:
    json.dump(classi, f, indent=2)


piano = bproc.object.create_primitive("PLANE", scale=[2.0, 2.0, 1.0])
piano.set_name("piano")
piano.set_cp("category_id", 0)
piano.enable_rigidbody(active=False, collision_shape="BOX", friction=0.9)

materiali_cc = []
if args.cc_textures and os.path.isdir(args.cc_textures):
    materiali_cc = bproc.loader.load_ccmaterials(args.cc_textures)
if not materiali_cc:
    print("Nessuna texture CC caricata: quando non uso una foto reale, il "
          "piano avra' un colore piatto random.\n  Va bene se hai gli sfondi "
          "reali: quelli coprono la maggior parte delle scene.")


sfondi_reali = []
if args.sfondi_reali and os.path.isdir(args.sfondi_reali):
    foto = sorted(f for f in glob.glob(os.path.join(args.sfondi_reali, "*"))
                  if f.lower().endswith((".png", ".jpg", ".jpeg")))
    for i, f in enumerate(foto):
        sfondi_reali.append(
            bproc.material.create_material_from_texture(f, f"sfondo_reale_{i}")
        )
    print(f"{len(sfondi_reali)} sfondi reali caricati da {args.sfondi_reali}")
else:
    print("Nessuno sfondo reale: uso solo texture CC. "
          "Consigliato: lancia prima cattura_sfondi.py")

hdri = [f for f in glob.glob(os.path.join(args.hdri_dir, "**", "*"), recursive=True)
        if f.lower().endswith((".hdr", ".exr"))]
if not hdri:
    raise SystemExit(
        f"Nessun HDRI in {args.hdri_dir}. "
        "Lancia: blenderproc download haven assets/haven"
    )
print(f"\n{len(materiali_cc)} materiali CC, {len(hdri)} HDRI disponibili.")


distrattori = []
for i, forma in enumerate(["CUBE", "CYLINDER", "CONE", "SPHERE", "MONKEY"]):
    d = bproc.object.create_primitive(forma)
    d.set_name(f"distrattore_{i}")
    d.set_cp("category_id", 0)
    d.hide(True)
    distrattori.append(d)

luce = bproc.types.Light()
luce.set_type("POINT")


mano = None
with open(args.mappa_classi) as f:
    _cfg_mano = json.load(f).get("mano")
if _cfg_mano:
    _path_mano = os.path.join(args.stl_dir, _cfg_mano["file"])
    if not os.path.exists(_path_mano):
        raise SystemExit(f"Mano non trovata: {_path_mano}")
    mano = bproc.loader.load_obj(_path_mano)[0]
    _scala_m = args.scala_mano if args.scala_mano is not None else args.scala_cad
    mano.set_scale([_scala_m] * 3)
    _mo = mano.blender_obj
    _mo.select_set(True)
    bpy.context.view_layer.objects.active = _mo
    bpy.ops.object.make_single_user(object=True, obdata=True)
    try:
        mano.persist_transformation_into_mesh(location=False, rotation=False, scale=True)
    except RuntimeError as e:
        print(f"  (scala mano non fusa: {e} - proseguo)")
    mano.set_origin(mode="CENTER_OF_VOLUME")
    mano.set_cp("category_id", classi[_cfg_mano["classe"]])
    mano.set_name("mano")
    mano.set_shading_mode("auto", 30)


    mano.clear_materials()
    _mat_mano = mano.new_material("pelle")
    _mat_mano.set_principled_shader_value("Base Color", [*COLORE_PELLE, 1.0])
    _mat_mano.set_principled_shader_value("Metallic", 0.0)
    _mat_mano.set_principled_shader_value("Roughness", 0.55)
    mano.hide(True)
    _bb = mano.get_bound_box()
    print(f"  Mano -> classe {_cfg_mano['classe']}, ingombro "
          f"{np.ptp(_bb[:, 0])*1000:.0f} x {np.ptp(_bb[:, 1])*1000:.0f} mm")


def piazza_mano(pezzi_in_scena):


    centri = np.array([o.get_location()[:2] for o in pezzi_in_scena])
    if len(centri) == 0:
        cx_p, cy_p = 0.0, 0.0
    else:
        cx_p, cy_p = centri.mean(axis=0)


    lato = random.choice(["sx", "dx", "alto", "basso"])
    off = 0.03
    x, y = {
        "sx":    (cx_p - off, cy_p),
        "dx":    (cx_p + off, cy_p),
        "alto":  (cx_p, cy_p + off),
        "basso": (cx_p, cy_p - off),
    }[lato]

    ang = {"sx": 0.0, "dx": np.pi, "alto": -np.pi / 2, "basso": np.pi / 2}[lato]


    if len(pezzi_in_scena) > 0:
        z_top = max(o.get_location()[2] for o in pezzi_in_scena)
    else:
        z_top = 0.0

    mezzo_spessore_mano = 0.012
    z = z_top + mezzo_spessore_mano + np.random.uniform(0.004, 0.02)
    mano.set_location([x, y, z])
    mano.set_rotation_euler([
        np.random.normal(0, np.deg2rad(15)),
        np.random.normal(0, np.deg2rad(15)),
        ang + np.random.normal(0, np.deg2rad(25)),
    ])
    mano.hide(False)


bproc.renderer.set_max_amount_of_samples(CAMPIONI)
bproc.renderer.set_noise_threshold(SOGLIA_RUMORE)
bproc.renderer.set_output_format(enable_transparency=False)
bproc.renderer.enable_segmentation_output(map_by=["instance", "category_id"])


def randomizza_materiale(obj):


    obj.clear_materials()
    mat = obj.new_material("meccano")

    cat = int(obj.get_cp("category_id"))                                         
    ammessi = colori_per_cat.get(cat)
    if ammessi:
        base = random.choice(ammessi)

        col = np.clip(np.array(base) * np.random.uniform(0.88, 1.12), 0, 1)
    else:


        if cat not in _classi_senza_colore_note:
            print(f"  ! classe id {cat} senza colore: controlla parts_catalog / mappa")
        g = np.random.uniform(0.3, 0.7)
        col = np.array([g, g, g])

    mat.set_principled_shader_value("Base Color", [*col, 1.0])


    mat.set_principled_shader_value("Metallic", 0.0)
    mat.set_principled_shader_value("Roughness", random.uniform(0.25, 0.70))


def posa_camera():

    loc = [
        np.random.uniform(-JITTER_XY, JITTER_XY),
        np.random.uniform(-JITTER_XY, JITTER_XY),
        np.random.uniform(args.z_min, args.z_max),
    ]
    roll = np.random.uniform(0, 2 * np.pi) if ROLL_LIBERO else np.random.normal(0, 0.05)
    rot = [np.random.normal(0, JITTER_TILT), np.random.normal(0, JITTER_TILT), roll]
    return bproc.math.build_transformation_mat(loc, rot)


n_val = max(1, int(args.scene * args.frazione_val))
dir_train = os.path.join(args.output, "train")
dir_val = os.path.join(args.output, "valid")

for scena in range(args.scene):
    bproc.utility.reset_keyframes()


    bproc.world.set_world_background_hdr_img(
        random.choice(hdri),
        strength=random.uniform(0.25, 1.6),
        rotation_euler=[0, 0, np.random.uniform(0, 2 * np.pi)],
    )

    if sfondi_reali and random.random() < args.prob_sfondo_reale:


        piano.replace_materials(random.choice(sfondi_reali))
        piano.set_scale([mezza_larghezza * 1.15, mezza_altezza * 1.15, 1.0])
    elif materiali_cc:
        piano.replace_materials(random.choice(materiali_cc))
        piano.set_scale([2.0, 2.0, 1.0])
    else:

        mat_piano = piano.new_material("piano_piatto")
        g = np.random.uniform(0.15, 0.6)
        mat_piano.set_principled_shader_value(
            "Base Color", [g, g, g * np.random.uniform(0.9, 1.1), 1.0])
        mat_piano.set_principled_shader_value("Roughness", np.random.uniform(0.5, 0.95))
        piano.replace_materials(mat_piano)
        piano.set_scale([2.0, 2.0, 1.0])


    piano.disable_rigidbody()
    piano.enable_rigidbody(active=False, collision_shape="BOX", friction=0.9)

    luce.set_location(bproc.sampler.shell(
        center=[0, 0, 0], radius_min=0.8, radius_max=2.5,
        elevation_min=25, elevation_max=89))
    luce.set_energy(random.uniform(20, 350))
    luce.set_color(np.random.uniform(0.85, 1.0, 3))


    regime = random.choices(
        ["sparso", "medio", "ammucchiato"], weights=[0.3, 0.45, 0.25]
    )[0]
    frazione_raggio, n_min, n_max = {
        "sparso":      (1.00, args.pezzi_min, max(args.pezzi_min, args.pezzi_max // 2)),
        "medio":       (0.65, args.pezzi_max // 2, args.pezzi_max),
        "ammucchiato": (0.32, args.pezzi_max // 2, args.pezzi_max),
    }[regime]
    raggio_x = RAGGIO_X * frazione_raggio
    raggio_y = RAGGIO_Y * frazione_raggio


    n = random.randint(n_min, min(n_max, len(pezzi)))
    attivi = random.sample(pezzi, n)
    for o in pezzi:
        o.hide(o not in attivi)


    dist_attivi = []
    for d in distrattori:
        d.hide(True)

    for o in attivi:
        randomizza_materiale(o)


    corpi = attivi + dist_attivi

    def campiona(obj):
        obj.set_location([
            np.random.uniform(-raggio_x, raggio_x),
            np.random.uniform(-raggio_y, raggio_y),


            np.random.uniform(0.02, 0.30 if regime == "ammucchiato" else 0.12),
        ])
        obj.set_rotation_euler(bproc.sampler.uniformSO3())

    bproc.object.sample_poses(objects_to_sample=corpi,
                              sample_pose_func=campiona, max_tries=200)

    for o in corpi:
        o.enable_rigidbody(active=True, collision_shape="CONVEX_HULL",
                           mass=0.02, friction=0.9,
                           linear_damping=0.5, angular_damping=0.5)

    bproc.object.simulate_physics_and_fix_final_poses(
        min_simulation_time=1.5, max_simulation_time=5.0, check_object_interval=0.5)

    for o in corpi:
        o.disable_rigidbody()


    if mano is not None:
        if random.random() < args.prob_mano:
            piazza_mano(attivi)
        else:
            mano.hide(True)


    for _ in range(args.viste_per_scena):
        bproc.camera.add_camera_pose(posa_camera())

    dati = bproc.renderer.render()

    bproc.writer.write_coco_annotations(
        dir_val if scena >= args.scene - n_val else dir_train,
        instance_segmaps=dati["instance_segmaps"],
        instance_attribute_maps=dati["instance_attribute_maps"],
        colors=dati["colors"],
        color_file_format="JPEG",
        mask_encoding_format="rle",
        append_to_existing_output=True,
    )

    if (scena + 1) % 25 == 0:
        print(f"[{scena+1}/{args.scene}] "
              f"{(scena+1)*args.viste_per_scena} immagini generate")


def pulisci_coco(cartella):


    src = os.path.join(cartella, "coco_annotations.json")
    if not os.path.exists(src):
        return
    with open(src) as f:
        d = json.load(f)

    id2nome = {c["id"]: c["name"] for c in d["categories"]}

    prima = len(d["annotations"])
    tenute = []
    for a in d["annotations"]:
        if a["category_id"] == 0:
            continue


        if a.get("area", 0) < args.area_min_px:
            continue
        w, h = a["bbox"][2], a["bbox"][3]
        if w < 8 or h < 8:
            continue
        tenute.append(a)

    d["annotations"] = tenute
    d["categories"] = [c for c in d["categories"] if c["id"] != 0]


    with open(os.path.join(cartella, "_annotations.coco.json"), "w") as f:
        json.dump(d, f)

    conteggi = {}
    for a in tenute:
        nome = id2nome.get(a["category_id"], str(a["category_id"]))
        conteggi[nome] = conteggi.get(nome, 0) + 1

    print(f"\n{cartella}: {len(d['images'])} immagini, {len(tenute)} istanze "
          f"({prima - len(tenute)} scartate perche' occluse o di sfondo)")
    if conteggi:
        vals = sorted(conteggi.values())
        print(f"  istanze per classe: min {vals[0]}, mediana "
              f"{vals[len(vals)//2]}, max {vals[-1]}")
        soglia = 0.5 * vals[len(vals) // 2]
        scarse = [k for k, v in conteggi.items() if v < soglia]
        if scarse:
            nomi_scarse = sorted(str(id2nome.get(k, k)) for k in scarse)
            print(f"  classi sotto-rappresentate: {', '.join(nomi_scarse)}")


for c in (dir_train, dir_val):
    pulisci_coco(c)

print("\nFatto. Ricorda: il val sintetico serve solo a controllare che il "
      "training converga.\nIl mAP che conta si misura su immagini REALI.")
