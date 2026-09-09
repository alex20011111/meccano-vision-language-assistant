# Relazione del progetto

Ho organizzato la relazione per seguire il percorso di lavoro: primo dataset fotografico, riconoscimento e tracking, guida con silhouette, interazione vocale, dati sintetici e valutazione. Per ogni parte descrivo il problema affrontato, le scelte di implementazione e i limiti rimasti.

## Consultazione

Il sorgente della pagina web è nel ramo [`docs/navigable-project-report`, cartella `report`](https://github.com/alex20011111/meccano-vision-language-assistant/tree/docs/navigable-project-report/report).

GitHub mostra il codice di un file HTML, non necessariamente la pagina impaginata. Per la consultazione locale scarico quel ramo, estraggo lo ZIP e apro `report/index.html` con un browser. La copia HTML autonoma della relazione completa incorpora anche la sezione UML e codice e le figure: si apre direttamente, senza avviare camera, modello o Python.

GitHub Pages è una modalità distinta di pubblicazione. La presenza dei sorgenti e dei workflow non indica da sola che il sito pubblico sia attivo.

## Percorso di lettura

**Contesto → dati iniziali → pipeline → moduli → UML e codice → risultati → riproducibilità → limiti.**

Nel primo passaggio descrivo l’addestramento del primo `best.pt` su **150 fotografie annotate manualmente in Roboflow**. Distinguo questa fase dalla generazione di scene con BlenderProc e dal successivo fine-tuning. Non uso i grafici di quest’ultimo per attribuire prestazioni al modello iniziale.

La [guida UML e codice](docs/UML_E_CODICE.md) collega le fasi ai nomi reali di classi, funzioni e metodi. Nell’appendice interattiva seguo le chiamate, apro le implementazioni e consulto i listati numerati. I diagrammi affiancano la spiegazione, senza sostituirla.

## Materiale visivo

La documentazione completa comprende la fotografia della camera, le schermate del piano e della composizione e gli undici grafici del detector. La foto del dispositivo non mostra il montaggio della RealSense sul banco. La schermata con TRIAL e cronometro appartiene a una versione precedente.

Conservo separatamente l’analisi delle loss, precision/recall, mAP, F1 e matrici di confusione. Segnalo le incongruenze del grafico AP per classe e non ricavo metriche precise da immagini quando mancano i dati numerici.

## Versione di riferimento

Ho mantenuto il **controllo del piano destro attivo**. G avvia la composizione solo quando i prerequisiti sono rispettati e non sostituisce una figura già attiva; N richiede un cambio quando il piano è libero. Tracking e verifica dei piazzamenti continuano durante il lavoro. Stop voce interrompe l’audio senza azzerare gli ID.

A090 e A823 sono refusi di etichettatura, non pezzi fisici. A132 è il codice corretto; A622 e A632 sono distinti; Hand è una classe ausiliaria.

## Riproducibilità

I listati commentati si riferiscono alle copie identificate nell’appendice tecnica. Pesi, dataset, CAD e configurazione del banco rimangono risorse separate. Tengo distinti i test software, le prove con l’hardware e la valutazione sperimentale dell’interazione.

[Pagina principale](README.md) · [Addestramento](docs/ADDESTRAMENTO.md) · [Scelte progettuali](docs/DECISIONS.md)
