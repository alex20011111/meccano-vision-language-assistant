# Decisioni consolidate del progetto

Questo documento distingue le decisioni confermate dall'autore dalle proposte presenti nelle conversazioni di sviluppo. Il codice e la relazione devono seguire questa versione dei requisiti.

## D01 — Il controllo del piano destro resta attivo

L'autore ha confermato che l'ultimo aggiornamento del controllo di occupazione, precedente alla richiesta di rimozione, funzionava. La successiva richiesta di eliminare il controllo è quindi superata. La baseline operativa è il pacchetto `meccano_fix_piano_destro` fornito nella conversazione.

Il controllo del piano destro è distinto dalla verifica dei singoli piazzamenti sulle silhouette. Avvio e cambio composizione devono rispettare il controllo di occupazione implementato nella baseline; non si documenta G come rigenerazione incondizionata.

## D02 — Tracking e voce

Il tracking resta visibile durante tutte le fasi. Stop voce interrompe il processo vocale locale senza fermare il ciclo video e senza azzerare gli ID. X conclude/azzera la composizione, non il tracking. Il messaggio di rientro dei pezzi è: **RIPORTARE I PEZZI NEL PIANO DI PARTENZA**.

## D03 — Tassonomia

- A090 e A823 sono refusi di etichettatura, non pezzi fisici. Non richiedono STL o silhouette e non costituiscono classi reali da valutare.
- A132 è il codice confermato dall'autore.
- A622 e A632 sono pezzi distinti; non devono essere unificati o rinominati automaticamente.
- Hand è una classe ausiliaria, non un pezzo da inserire nella composizione.

Conservare l'ordine degli indici nei checkpoint e nelle annotazioni esistenti. Non cancellare due nomi dal mezzo di una lista senza una migrazione coerente di etichette e modello.

## D04 — Perimetro della relazione

Il prototipo integra visione RGB-D, YOLO, ByteTrack, stabilizzazione temporale, geometria CAD e interazione vocale con LLM locale. Nei sorgenti forniti non è documentata l'attuazione di un robot, una pipeline ROS/ROS2 o un VLM che riceva direttamente immagini. Questi temi appartengono al contesto formativo o agli sviluppi futuri, non ai risultati implementati.

## D05 — Provenienza delle evidenze

Le schermate caricate dall'autore sono evidenze visive del prototipo; una schermata con TRIAL e cronometro documenta una versione storica. La raccolta dati sperimentale rimane esclusa dal runtime attuale. Gli export integrali delle conversazioni non vengono pubblicati.

I grafici di addestramento restano inalterati. Il grafico AP per classe presenta incongruenze rispetto alla tassonomia e alla matrice di confusione: va verificato sugli output numerici originali e non è una graduatoria certificata.
