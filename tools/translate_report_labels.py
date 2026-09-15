import base64
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

HASHES = {
    '9d9c7a1863b9c98577e52144aa2515f48b5c7b49be444e3d542bd7cfa1a15a61': 1,
    'a17c9ee78b28626e78372b171de7fdf4c55645ea23dfd94d6300af10dd8c5d2a': 2,
    '3300fe394749f16da2caaec0d3059c83fa3e3eefafa0c79a81c9fb7a0fde203d': 3,
    'e5b3a0c208cbf16dcb96573a15c2b9e5328fc82897c146c2b10deb45ca3478ac': 4,
    'ff2354af9f756177b6f47cb5633dcbfb01523f52d035171daa62b3096ec9fb85': 14,
    'cfdf2b9b3845e8000a70d85ee676e516e1c67cbb2273d6da534ad7dc47dac6a7': 15,
    '165d2abee3ae220222346d9ed413eff9466445513eb45c150b1486758cfcbb67': 16,
    'd627554afc9701b88ee62ef31b0a47a95143e0967b0c44ff220aa94aee90e05c': 17,
    'c93dba740601f01124673c2f2a34650fea3b1d775d747e93d877a153d60851a8': 18,
    '8d649e012352d4548eb7890eacc5dda37dab1824796c11dc21d0638f38f2e8c3': 19,
    '295b683ef5f6c6ffd69d4814f74cc13f9df4ab6531f4e047eccfcd5baeb729cd': 20,
    'd234864f2fd87e47e6d338485e295abd1cc2c41d6d1987439842f79e9b1d2bfd': 22,
    '3c5bde594e8f8dca3ab70f240db9a6acb9ec8bd27ddc4fe257f4f35b40b49f29': 23,
    'ce179ebd8f9ebf9dd0e17343e599af55e8116e590e2af199f43c3718154b3213': 24,
}
TITLES = {
    14: ('Training losses', 'Loss'),
    15: ('Validation losses', 'Loss'),
    16: ('Training and validation loss sums', 'Total loss'),
    17: ('Precision and recall', 'Value'),
    18: ('Mean average precision', 'mAP'),
    19: ('F1 from aggregate precision and recall', 'F1 score'),
    20: ('Learning-rate schedule', 'Learning rate'),
    22: ('Confusion matrix (counts)', 'Predicted class'),
    23: ('Confusion matrix (column-normalised)', 'Predicted class'),
    24: ('Reported per-class mAP50 (class mapping unverified)', ''),
}
FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def font(size):
    return ImageFont.truetype(FONT_PATH, max(8, round(size)))


def label(image, text, box, size=22, color='black', background='white'):
    draw = ImageDraw.Draw(image)
    draw.rectangle(box, fill=background)
    f = font(size)
    while draw.textbbox((0, 0), text, font=f)[2] > box[2]-box[0]-10 and size > 8:
        size -= 1
        f = font(size)
    b = draw.textbbox((0, 0), text, font=f)
    x = (box[0]+box[2]-(b[2]-b[0]))/2-b[0]
    y = (box[1]+box[3]-(b[3]-b[1]))/2-b[1]
    draw.text((x, y), text, font=f, fill=color)


def vertical_label(image, text, strip):
    height = image.height
    ImageDraw.Draw(image).rectangle((0, 0, strip, height), fill='white')
    layer = Image.new('RGB', (int(height*.7), strip), 'white')
    label(layer, text, (0, 0, layer.width-1, strip-1), size=20)
    layer = layer.rotate(90, expand=True)
    image.paste(layer, (0, (height-layer.height)//2))


def translate(raw, index):
    image = Image.open(io.BytesIO(raw)).convert('RGB')
    before = np.asarray(image).copy()
    w, h = image.size
    keep = np.zeros((h, w), dtype=bool)
    draw = ImageDraw.Draw(image)
    if index in TITLES:
        title, ylab = TITLES[index]
        if index in (22, 23):
            label(image, title, (0, 0, w-1, int(h*.028)), 25)
            label(image, 'True class', (0, int(h*.97), w-1, h-1), 23)
            vertical_label(image, ylab, int(w*.024))
            keep[int(h*.031):int(h*.95), int(w*.09):int(w*.966)] = True
        elif index == 24:
            label(image, title, (0, 0, w-1, 40), 22)
            keep[42:, :] = True
        else:
            label(image, title, (0, 0, w-1, 64 if index == 16 else 40), 24)
            label(image, 'Epoch', (0, h-34, w-1, h-1), 20)
            vertical_label(image, ylab, 32)
            keep[69 if index == 16 else 43:h-35, 84:w-12] = True
            if index == 16:
                draw.rectangle((1078, 82, 1214, 139), fill='white')
                draw.text((1085, 88), 'train (sum)', font=font(20), fill='black')
                draw.text((1085, 115), 'val (sum)', font=font(20), fill='black')
                keep[82:140, 1078:1215] = False
    elif index == 1:
        sx, sy = w/1664, h/927
        label(image, 'Training summary', (0, 0, w-1, int(34*sy)), round(23*sx))
        keep[:, :] = True
        keep[:int(35*sy)] = False
        for cy in (465, 909):
            for cx in (295, 847, 1400):
                box = tuple(round(v) for v in ((cx-72)*sx, (cy-10)*sy, (cx+72)*sx, (cy+12)*sy))
                label(image, 'Epoch', box, round(16*sx))
                x1, y1, x2, y2 = box
                keep[y1:y2+1, x1:x2+1] = False
    elif index == 2:
        keep[:, :] = True
        for x, text in ((.008, 'STARTING AREA'), (.519, 'ASSEMBLY AREA')):
            x0, y0 = int(w*x), int(h*.968)
            box = (x0, y0, min(w-1, x0+int(w*.16)), h-1)
            label(image, text, box, int(w*.011), '#eeeeee', '#747972')
            keep[y0:, x0:box[2]+1] = False
    elif index == 4:
        box = (int(w*.51), int(h*.014), int(w*.675), int(h*.061))
        label(image, 'Assembly: 2/5', box, int(w*.018), '#f1f1ed', '#777d75')
        keep[:, :] = True
        x1, y1, x2, y2 = box
        keep[y1:y2+1, x1:x2+1] = False
    elif index == 3:
        sx, sy = w/1654, h/929
        labels = ['[G] Start composition', '[V] Verify parts', '[N] Change composition', '[R] Voice query', '[S] Stop voice', '[X] Finish / reset']
        for i, text in enumerate(labels):
            box = (int((11+i*276.4)*sx), int(12*sy), min(w-2, int((276+i*276.4)*sx)), int(57*sy))
            label(image, text, box, int(17*sx), '#eceeea', '#373e35' if i else '#292b29')
        draw.rectangle((int(1285*sx), int(78*sy), w-1, int(780*sy)), fill='#1d1d1d')
        rows = [
            ('COMPOSITION PARTS', 1293, 88, 17, '#dddddd'),
            ('0 / 6 completed', 1293, 120, 16, '#dddddd'),
            ('Code     Done/Total    On right', 1293, 153, 14, '#dddddd'),
            ('A003       0/1          0', 1293, 187, 15, '#dddddd'),
            ('red straight plate', 1300, 214, 14, '#aaaaaa'),
            ('A004       0/1          0', 1293, 242, 15, '#dddddd'),
            ('grey straight plate', 1300, 268, 14, '#aaaaaa'),
            ('A050       0/1          0', 1293, 297, 15, '#dddddd'),
            ('red oval pin', 1300, 323, 14, '#aaaaaa'),
            ('C658       0/3          0', 1293, 352, 15, '#dddddd'),
            ('red nut', 1300, 377, 14, '#aaaaaa'),
            ('[V] Locate the missing parts', 1293, 433, 16, '#ded91a'),
            ('RIGHT-HAND AREA CHECK', 1293, 488, 16, '#bfbbaa'),
            ('RIGHT AREA CLEAR', 1293, 516, 15, '#80c67c'),
        ]
        for text, x, y, size, color in rows:
            draw.text((round(x*sx), round(y*sy)), text, font=font(size*sx), fill=color)
        draw.rectangle((0, int(797*sy), w, h), fill='#161616')
        draw.text((int(14*sx), int(807*sy)), 'Left: 6 recognised | Completed: 0/6 | RIGHT AREA CLEAR | Voice: IDLE', font=font(16*sx), fill='#dddddd')
        draw.text((int(14*sx), int(840*sy)), 'Composition 1: 6 silhouettes for 6 recognised parts on the left.', font=font(16*sx), fill='#d2c98f')
        for text, x in [('STARTING AREA', 15), ('ASSEMBLY AREA', 650)]:
            x0, y0 = int(x*sx), int(767*sy)
            draw.rectangle((x0, y0, x0+int(133*sx), y0+int(19*sy)), fill='#747972')
            draw.text((x0, y0), text, font=font(11*sx), fill='#dddddd')
        keep[int(73*sy):int(765*sy), :int(1270*sx)] = True
    else:
        raise ValueError('Unrecognised figure index')
    if not np.array_equal(before[keep], np.asarray(image)[keep]):
        raise RuntimeError('Protected figure data changed')
    out = io.BytesIO()
    image.save(out, format='PNG', optimize=True)
    return out.getvalue()


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    paths = [root/'report/index.html', root/'Meccano_Report_English.html']
    updates, checks, found = {}, {}, set()
    for path in paths:
        if not path.is_file():
            raise SystemExit('Missing English HTML: '+str(path))
        text = path.read_text(encoding='utf-8')
        soup = BeautifulSoup(text, 'html.parser')
        if soup.html is None or soup.html.get('lang') != 'en':
            raise SystemExit('The report must already be in English')
        for tag in soup.find_all('img'):
            src = tag.get('src', '')
            if not src.startswith(('data:image/png;base64,', 'data:image/webp;base64,')):
                continue
            raw = base64.b64decode(src.split(',', 1)[1])
            sha = hashlib.sha256(raw).hexdigest()
            if sha not in HASHES:
                continue
            index = HASHES[sha]
            found.add(index)
            if sha not in checks:
                payload = translate(raw, index)
                replacement = 'data:image/png;base64,'+base64.b64encode(payload).decode('ascii')
                checks[sha] = {'replacement': replacement, 'source_sha256': sha, 'translated_sha256': hashlib.sha256(payload).hexdigest(), 'protected_data_pixels_unchanged': True, 'figure': index}
            text = text.replace(src, checks[sha]['replacement'])
        if checks and 'id="figure-language-note"' not in text:
            note = '<p id="figure-language-note" style="font-size:0.9em;padding:1em">Figure labels and interface annotations have been translated into English. The plotted curves, matrix values, observed counts and camera regions are unchanged. These are editorial translations of existing figures, not new experimental runs. The per-class chart remains unverified; a train/validation loss gap alone is not an overfitting test.</p>'
            text = text.replace('</body>', note+'</body>')
        updates[path] = text
    if found and found != set(HASHES.values()):
        raise SystemExit('Incomplete figure match; missing '+str(sorted(set(HASHES.values())-found)))
    if not found:
        if all('figure-language-note' in text for text in updates.values()):
            print('English figure labels already present; no changes.')
            return
        raise SystemExit('No original figure hashes matched; refusing an unverified translation')
    for path, text in updates.items():
        path.write_text(text, encoding='utf-8')
    manifest = {sha: {k:v for k,v in record.items() if k != 'replacement'} for sha,record in checks.items()}
    (root/'docs').mkdir(exist_ok=True)
    (root/'docs/FIGURE_TRANSLATION.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print('Translated', len(found), 'unique figures in', len(updates), 'HTML files; protected data pixels unchanged.')


if __name__ == '__main__':
    main()
