import argparse
import json
import os
import random
import shutil

import albumentations as A
import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--sintetico", required=True,
                help="cartella dataset_sintetico (con classi.json e train/)")
ap.add_argument("--output", default="dataset_yolo")
ap.add_argument("--target", type=int, default=2000,
                help="numero totale di immagini di train che vuoi ottenere "
                     "(originali + augmentate)")
ap.add_argument("--val_frac", type=float, default=0.12,
                help="quota di immagini ORIGINALI tenuta per la validazione")
ap.add_argument("--area_min_px", type=int, default=250)
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

random.seed(args.seed)
np.random.seed(args.seed)


path_classi = os.path.join(args.sintetico, "classi.json")
if not os.path.exists(path_classi):
    raise SystemExit(f"Non trovo {path_classi}. E' generato da genera_dataset_meccano.py "
                     "insieme al dataset: controlla di puntare alla cartella giusta.")

with open(path_classi, encoding="utf-8") as f:
    classi = json.load(f)


max_id = max(classi.values())
nomi_ordinati = [None] * max_id
for nome, cid in classi.items():
    nomi_ordinati[cid - 1] = nome
print(f"{len(nomi_ordinati)} classi lette da classi.json (ordine preservato per il fine-tuning).")


dir_train_in = os.path.join(args.sintetico, "train")
dir_img_in = os.path.join(dir_train_in, "images")
js_path = os.path.join(dir_train_in, "coco_annotations.json")
if not os.path.exists(js_path):

    js_path = os.path.join(dir_train_in, "_annotations.coco.json")
if not os.path.exists(js_path):
    raise SystemExit(f"Non trovo ne' coco_annotations.json ne' _annotations.coco.json in {dir_train_in}")

with open(js_path, encoding="utf-8") as f:
    coco = json.load(f)

per_img = {}
for a in coco["annotations"]:
    per_img.setdefault(a["image_id"], []).append(a)


def bbox_valide(img_info):

    out = []
    for a in per_img.get(img_info["id"], []):
        if a["category_id"] == 0:
            continue
        if a.get("area", a["bbox"][2] * a["bbox"][3]) < args.area_min_px:
            continue
        x, y, w, h = a["bbox"]
        if w <= 1 or h <= 1:
            continue


        cid0 = a["category_id"] - 1
        if cid0 < 0 or cid0 >= len(nomi_ordinati):
            continue
        out.append((cid0, x, y, w, h))
    return out


immagini_valide = []
for img in coco["images"]:
    src = os.path.join(dir_img_in, os.path.basename(img["file_name"]))
    if not os.path.exists(src):
        continue
    box = bbox_valide(img)
    if not box:
        continue
    immagini_valide.append((img, src, box))

if not immagini_valide:
    raise SystemExit("Nessuna immagine con annotazioni valide trovata. Controlla il dataset.")

print(f"{len(immagini_valide)} immagini con almeno un'annotazione valida.")


random.shuffle(immagini_valide)
n_val = max(1, int(len(immagini_valide) * args.val_frac))
val_set = immagini_valide[:n_val]
train_set = immagini_valide[n_val:]
print(f"Split originali: {len(train_set)} train, {len(val_set)} val")

for split in ("train", "val"):
    os.makedirs(os.path.join(args.output, split, "images"), exist_ok=True)
    os.makedirs(os.path.join(args.output, split, "labels"), exist_ok=True)


def scrivi_yolo(path_txt, box_list, W, H):
    righe = []
    for cid0, x, y, w, h in box_list:
        cx, cy = (x + w / 2) / W, (y + h / 2) / H
        wn, hn = w / W, h / H
        cx, cy = min(max(cx, 0), 1), min(max(cy, 0), 1)
        wn, hn = min(wn, 1), min(hn, 1)
        righe.append(f"{cid0} {cx:.6f} {cy:.6f} {wn:.6f} {hn:.6f}")
    with open(path_txt, "w") as f:
        f.write("\n".join(righe))


def copia_originale(img_info, src, box_list, split):
    nome = os.path.basename(img_info["file_name"])
    dst_img = os.path.join(args.output, split, "images", nome)
    shutil.copy2(src, dst_img)
    stem = os.path.splitext(nome)[0]
    dst_lbl = os.path.join(args.output, split, "labels", stem + ".txt")
    scrivi_yolo(dst_lbl, box_list, img_info["width"], img_info["height"])


for img, src, box in val_set:
    copia_originale(img, src, box, "val")
for img, src, box in train_set:
    copia_originale(img, src, box, "train")


augment = A.Compose(
    [
        A.Rotate(limit=25, border_mode=cv2.BORDER_REFLECT_101, p=0.8),
        A.RandomBrightnessContrast(brightness_limit=0.25, contrast_limit=0.25, p=0.8),
        A.HueSaturationValue(hue_shift_limit=8, sat_shift_limit=20, val_shift_limit=15, p=0.5),
        A.OneOf([
            A.GaussianBlur(blur_limit=(3, 5)),
            A.MotionBlur(blur_limit=(3, 7)),
        ], p=0.35),
        A.GaussNoise(std_range=(0.02, 0.08), p=0.3),
        A.ImageCompression(quality_range=(55, 90), p=0.4),
        A.RandomShadow(p=0.15),
    ],
    bbox_params=A.BboxParams(format="coco", label_fields=["category_ids"],
                             min_visibility=0.25),
)

n_originali_train = len(train_set)
n_target_train = args.target - len(val_set)
n_da_generare = max(0, n_target_train - n_originali_train)

print(f"\nAugmentation: genero {n_da_generare} immagini extra per arrivare a "
      f"~{args.target} totali ({n_originali_train} originali + {n_da_generare} aumentate "
      f"in train, {len(val_set)} in val).")

generate = 0
tentativi = 0
max_tentativi = n_da_generare * 4 + 20

while generate < n_da_generare and tentativi < max_tentativi:
    tentativi += 1
    img_info, src, box_list = random.choice(train_set)
    frame = cv2.imread(src)
    if frame is None:
        continue

    bboxes = [(x, y, w, h) for _, x, y, w, h in box_list]
    cat_ids = [cid0 for cid0, *_ in box_list]

    try:
        aug = augment(image=frame, bboxes=bboxes, category_ids=cat_ids)
    except Exception:
        continue

    if not aug["bboxes"]:
        continue

    nome_base = os.path.splitext(os.path.basename(img_info["file_name"]))[0]
    nome_out = f"{nome_base}_aug{generate:05d}.jpg"
    cv2.imwrite(os.path.join(args.output, "train", "images", nome_out), aug["image"])

    H, W = aug["image"].shape[:2]
    box_out = [(cid, *bb) for cid, bb in zip(aug["category_ids"], aug["bboxes"])]
    scrivi_yolo(os.path.join(args.output, "train", "labels",
                             nome_out.replace(".jpg", ".txt")), box_out, W, H)
    generate += 1

    if generate % 200 == 0:
        print(f"  {generate}/{n_da_generare} immagini aumentate...")

print(f"Aumentate {generate} immagini (tentativi falliti: {tentativi - generate}).")


with open(os.path.join(args.output, "data.yaml"), "w", encoding="utf-8") as f:
    f.write(f"path: {os.path.abspath(args.output)}\n")
    f.write("train: train/images\n")
    f.write("val: val/images\n")
    f.write(f"nc: {len(nomi_ordinati)}\n")
    f.write("names:\n")
    for i, n in enumerate(nomi_ordinati):
        f.write(f"  {i}: {n}\n")

n_train_finale = len(os.listdir(os.path.join(args.output, "train", "images")))
n_val_finale = len(os.listdir(os.path.join(args.output, "val", "images")))
print(f"\nFatto. train: {n_train_finale} immagini | val: {n_val_finale} immagini")
print(f"data.yaml: {os.path.join(args.output, 'data.yaml')}")
