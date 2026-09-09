# Addestramento: dalle fotografie annotate al dataset sintetico

## 1. Il primo modello

Per ottenere il primo `best.pt` ho utilizzato **150 fotografie, etichettate manualmente su Roboflow**. Il primo riconoscimento dei componenti Meccano è quindi partito da un dataset fotografico annotato a mano, non da immagini generate dai CAD.

Le 150 fotografie descrivono il dataset iniziale, non il numero di immagini per classe e non il numero di epoche. Non riporto una suddivisione numerica in train, validation e test per questa fase, perché non ho incluso nella documentazione il relativo manifest. Allo stesso modo, non attribuisco al primo run iperparametri o metriche ricavati dai grafici del fine-tuning successivo.

Roboflow è lo strumento con cui ho annotato le immagini. Questa informazione non implica che l’addestramento sia stato eseguito sul servizio cloud di Roboflow.

## 2. Dal detector al tracking

Ho utilizzato il primo modello come punto di partenza del programma RGB-D. Il problema affrontato in questa fase era l’instabilità della classe assegnata allo stesso pezzo tra fotogrammi: il solo rilevamento non bastava a fornire un’informazione continua all’operatore.

Ho quindi integrato ByteTrack per l’associazione temporale, uno storico di osservazioni per il voto della classe e il lock per conservarla. Il recupero tramite ghost gestisce alcune perdite temporanee dei track. Questi interventi riguardano il comportamento della pipeline: non li considero un nuovo addestramento e non li presento come un aumento misurato della mAP.

## 3. Il secondo percorso: dati sintetici dai CAD

Successivamente ho riutilizzato i modelli CAD per aumentare la varietà delle scene disponibili. Con BlenderProc ho lavorato su disposizione dei pezzi, rotazioni, materiali, illuminazione, sfondi e occlusioni della mano. Le annotazioni derivano dalla scena simulata, anziché da un nuovo lavoro manuale su ogni render.

Il percorso è:

```text
150 fotografie → annotazione manuale in Roboflow → primo addestramento → best.pt iniziale
                                                                              │
CAD / STL → scene BlenderProc → annotazioni COCO → preparazione YOLO ────────────┤
                                                                              ↓
                                                                 fine-tuning successivo
```

I due percorsi hanno origini diverse: le fotografie costituiscono il dataset iniziale; i render e le loro trasformazioni appartengono alla preparazione successiva.

## 4. Conversione e augmentation

`crea_mappa.py` legge l’ordine delle classi del checkpoint e collega i codici agli STL e al catalogo. `genera_dataset_meccano.py` produce le scene e le annotazioni; `prepara_addestramento.py` prepara immagini, etichette YOLO e `data.yaml`.

Il preparatore divide gli originali prima delle trasformazioni e applica l’augmentation soltanto al train. Nel log di questa fase ho riportato **898 immagini originali e 980 aumentate nel train, più 122 immagini di validazione**, per un totale di 2.000. Queste quantità non sono la suddivisione delle 150 fotografie iniziali e non indicano 2.000 fotografie originali.

Lo split del preparatore è per immagine. Per valutare l’indipendenza dei gruppi devo considerare anche eventuali viste della stessa scena e i dati già utilizzati nei pesi di partenza.

## 5. Fine-tuning e interpretazione dei grafici

Ho proseguito l’addestramento dal `best.pt` esistente usando il dataset sintetico preparato successivamente. Distinguo questo fine-tuning dal primo addestramento sulle fotografie annotate a mano.

I grafici della relazione mostrano 50 epoche del percorso successivo. Nei comandi annotati durante lo sviluppo compare anche una configurazione da 60 epoche; senza il log completo e `args.yaml` non attribuisco una causa precisa a questa differenza.

La validazione sintetica permette di esaminare convergenza e prestazioni nel dominio del rendering. Non è, da sola, un test del sistema sul banco reale. Non confronto quantitativamente primo e secondo modello senza valutarli sullo stesso insieme indipendente e con le stesse condizioni. Un’immagine già utilizzata per addestrare il primo modello non diventa un test indipendente dopo il fine-tuning.

## 6. Errori di etichettatura e continuità degli indici

**A090 e A823 sono refusi di etichettatura, non componenti fisici.** A132 è il codice corretto; A622 e A632 restano distinti; Hand è una classe ausiliaria.

Non elimino semplicemente due nomi dal centro della lista di un checkpoint: cambierebbe la corrispondenza degli indici successivi. La pulizia delle annotazioni deve essere esplicita e verificata, senza assegnare automaticamente A090 o A823 a un altro componente.

Nel grafico AP per classe le barre associate ai refusi non sono interpretabili come prestazioni su pezzi reali. Conservo i grafici e segnalo l’incongruenza; una valutazione corretta richiede gli output numerici e la mappatura usata nell’esportazione.

## 7. Materiale da conservare insieme a ogni modello

Per ricostruire un run tengo separati checkpoint, versione delle annotazioni, elenco delle immagini di ciascuno split, mappa dei codici, configurazione e risultati. I file da associare al modello comprendono `best.pt`, `data.yaml`, `args.yaml` e `results.csv`, quando disponibili. Non assegno valori mancanti per analogia con altre prove.

[UML e percorso del codice](UML_E_CODICE.md) · [Scelte progettuali](DECISIONS.md) · [Pagina principale](../README.md)
