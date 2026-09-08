# Relazione web del progetto

La relazione navigabile è in `index.html`. È una documentazione del prototipo, non una dimostrazione di controllo robotico e non esegue la camera o il modello nel browser.

## Criteri editoriali

- Spiegare il problema prima delle librerie: riconoscere, mantenere identità temporali, localizzare un pezzo su richiesta e guidare una composizione.
- Distinguere il percorso offline CAD/dataset/addestramento dal ciclo online RGB-D/tracking/interazione.
- Affiancare ai diagrammi gli ingressi, le uscite, lo scopo e i limiti di ogni passaggio.
- Tenere separati risultati osservabili nei grafici, informazioni dichiarate dall'autore, prove simulate e misure ancora assenti.
- A090 e A823 sono refusi di etichettatura, non pezzi fisici. A132 è il codice confermato. A622 e A632 sono distinti. Hand è una classe ausiliaria.
- Non ricavare nuove metriche precise da immagini, non attribuire prestazioni di tracking o di interazione al solo mAP del detector.
- Non pubblicare esportazioni integrali delle conversazioni, percorsi personali, credenziali o file di acquisizione.

## Materiale fotografico da completare

Servono una foto del banco con la RealSense, una schermata attuale della composizione e una della verifica dei pezzi. Le immagini del banco non vengono sostituite con fotografie generate. Le schermate di test simulate devono essere etichettate come tali.

## Nota sul requisito G

Nella conversazione di consegna è stata richiesta la rigenerazione a ogni G senza controllo del piano destro. Il documento `docs/DECISIONS.md` presente su main descrive invece un requisito differente. Questa documentazione segnala la divergenza e non modifica silenziosamente il runtime mentre si consolida la versione del repository.

## Consultazione locale

Dalla radice del repository:

```bash
python -m http.server 8000
```

Aprire `http://localhost:8000/report/`. Il server è soltanto un visualizzatore locale della documentazione; non carica immagini o audio dal banco.
