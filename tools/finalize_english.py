import ast
import hashlib
import json
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path.cwd()
REPORT = ROOT / 'report/index.html'
RENAMES = {'crea_mappa': 'create_class_map', 'genera_dataset_meccano': 'generate_meccano_dataset', 'prepara_addestramento': 'prepare_training', 'prova_colori': 'preview_colors'}
REPLACEMENTS = {
    'RIPORTARE I PEZZI NEL PIANO DI PARTENZA': 'RETURN THE PARTS TO THE STARTING AREA',
    'Piano destro occupato': 'Right-hand area occupied', 'Piano destro libero': 'Right-hand area clear',
    '[VERIFICA]': '[CHECK]', 'Non localizzati': 'Not located', 'sul piano sinistro': 'on the left-hand surface',
    'errore simulato': 'simulated error', 'snapshot non aggiornato': 'stale snapshot',
    'Condizione non raggiunta; stato=': 'Condition not reached; state=', '; errore=': '; error=',
    'frase di prova': 'test sentence', 'Voce interrotta.': 'Voice stopped.',
    'troppo largo': 'too wide', 'confidenza bassa': 'low confidence', 'occupato': 'occupied', 'Attendo': 'Waiting',
    'NON DISPONIBILE': 'UNAVAILABLE', 'CONTROLLO DX': 'RIGHT CHECK', 'A003 - senza ID': 'A003 - no ID',
    'x2=940.0; linea=640': 'x2=940.0; line=640', 'Candidati grezzi scartati: 1': 'Rejected raw candidates: 1',
    'MANO': 'HAND', 'Mano': 'Hand', 'riepilogo': 'summary',
    '20594ba114848abf39d24b79519bc1c25452904888cb58f11d11606f34955268': '3aced9c03dca8cb48283959114d8410d203a2f0140bc35c347bb8d3e80fe26d7',
}

def translate_names(text):
    for old, new in RENAMES.items():
        text = text.replace(old, new)
    return text

raw = REPORT.read_bytes()
actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
if actual != 'd9977d9b02f0752fac818b0ee961dfa8810bb4d3':
    raise SystemExit('The report changed. Review the new version before restoring sources.')
soup = BeautifulSoup(raw.decode('utf-8'), 'html.parser')
data = json.loads(soup.find(id='uc-data').string)
if len(data['files']) != 15:
    raise SystemExit('Expected fifteen indexed modules.')
for entry in data['files']:
    filename = entry['filename']
    if Path(filename).name != filename or not filename.endswith('.py'):
        raise SystemExit('Unexpected source path: ' + filename)
    text = '\n'.join(entry['lines']) + '\n'
    if hashlib.sha256(text.encode()).hexdigest() != entry['display_sha256']:
        raise SystemExit('Embedded source integrity failed: ' + filename)
    ast.parse(text)
    text = translate_names(text)
    text = text.replace(':.2f} e {args.z_max', ':.2f} and {args.z_max')
    text = text.replace(':.3f} a {mm_per_px_max', ':.3f} to {mm_per_px_max')
    target = translate_names(filename)
    (ROOT / target).write_text(text, encoding='utf-8')
    entry['filename'] = target
    entry['lines'] = text.splitlines()
    entry['sha256'] = entry['display_sha256'] = hashlib.sha256(text.encode()).hexdigest()
for path in (ROOT / 'tests').glob('*.py'):
    text = path.read_text(encoding='utf-8')
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    text = translate_names(text)
    ast.parse(text)
    path.write_text(text, encoding='utf-8')
for old in RENAMES:
    (ROOT / (old + '.py')).unlink(missing_ok=True)
soup.find(id='uc-data').string = json.dumps(data, ensure_ascii=False).replace('</','<\\/')
report_text = translate_names(str(soup))
REPORT.write_text(report_text, encoding='utf-8')
(ROOT / 'Meccano_Report_English.html').write_text(report_text, encoding='utf-8')
(ROOT / 'Meccano_Report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=report/index.html"><title>Meccano project report</title><p><a href="report/index.html">Open the English project report</a></p></html>\n',encoding='utf-8')
for path in list((ROOT / 'docs').glob('*.md')) + [ROOT / 'README.md',ROOT / 'WEB_REPORT.md']:
    if path.exists():
        path.write_text(translate_names(path.read_text(encoding='utf-8')),encoding='utf-8')
index = ['# Source index', '', 'The entries below refer to the English files published in this repository.', '']
for entry in data['files']:
    name = translate_names(entry['filename'])
    index.extend(['## '+name, '', entry['purpose'], '', '| Symbol | Kind | Lines |', '|---|---|---|'])
    for symbol in entry['symbols']:
        start, end = symbol['line'], symbol['end']
        index.append(f"| `{symbol['name']}` | {symbol['kind']} | [{start}–{end}](../{name}#L{start}-L{end}) |")
    index.append('')
(ROOT / 'docs/SOURCE_INDEX.md').write_text('\n'.join(index),encoding='utf-8')
for old in ('RELAZIONE_WEB.md','docs/ADDESTRAMENTO.md','docs/SORGENTI.md','docs/UML_E_CODICE.md','Meccano Guida.html'):
    (ROOT / old).unlink(missing_ok=True)
print('Restored 15 English modules and updated tests, source index and embedded listings.')
