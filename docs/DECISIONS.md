# Scelte progettuali

In queste note raccolgo le scelte che ho mantenuto nel prototipo e distinguo il funzionamento corrente dalle alternative considerate durante lo sviluppo.

## D01 — Controllo del piano di montaggio

Ho mantenuto il controllo di occupazione del piano destro nella versione `meccano_fix_piano_destro`. Avvio e cambio composizione rispettano questo controllo; G non rigenera una figura già attiva.

Il controllo del piano è distinto dalla verifica del singolo piazzamento sulla silhouette. La presenza di un pezzo fuori dalle sagome può impedire una nuova generazione senza corrispondere a uno slot completato. I rilevamenti utilizzati per il controllo devono essere coerenti con i filtri di plausibilità e con la diagnostica mostrata a schermo.

## D02 — Tracking continuo e arresto della voce

Ho mantenuto i riquadri del tracking durante tutte le fasi. Stop voce interrompe il processo vocale locale senza chiudere la camera o azzerare gli ID. X conclude e azzera la composizione, non il tracking.

Se rimangono pezzi nella zona di montaggio dopo X o al completamento, l’avviso scritto e vocale è **RIPORTARE I PEZZI NEL PIANO DI PARTENZA**. L’arresto della voce non deve cancellare l’informazione visiva sullo stato del piano.

## D03 — Codici fisici e indici del modello

A090 e A823 sono errori introdotti durante l’etichettatura: non rappresentano pezzi reali e non richiedono STL o silhouette. A132 è il codice corretto del perno; A622 e A632 sono pezzi distinti. Hand è una classe ausiliaria, esclusa dall’inventario della composizione.

Tengo separata questa tassonomia dall’ordine numerico delle classi in un checkpoint. Non elimino nomi intermedi senza una migrazione coerente delle annotazioni e della configurazione. Dove il codice di riferimento non applica ancora tutti i vincoli del catalogo, lo segnalo nella lettura dei sorgenti.

## D04 — Perimetro del prototipo

Ho integrato percezione RGB-D, YOLO, ByteTrack, stabilizzazione temporale, geometria CAD e interazione vocale con un LLM locale. Il modello linguistico interpreta la richiesta; non calcola coordinate e non controlla attuatori.

Il prototipo non comprende un braccio robotico, nodi ROS/ROS2 o un VLM con ingresso diretto delle immagini. Questi aspetti appartengono al contesto formativo e agli sviluppi possibili, non alle funzioni implementate.

## D05 — Documentazione delle prove

Ho mantenuto le schermate del prototipo e i grafici di addestramento come materiali distinti. La schermata con TRIAL e cronometro documenta una versione precedente; la raccolta dati sperimentale non è attiva nel runtime di riferimento.

Le curve del detector non misurano la continuità degli ID, la qualità della risposta vocale o il beneficio per l’operatore. Il grafico AP per classe richiede inoltre una verifica sugli output numerici originali, perché presenta incongruenze con la tassonomia e le matrici di confusione. Non lo uso come graduatoria delle prestazioni dei componenti.

## D06 — Origine del primo best.pt

Il primo modello è stato addestrato su **150 fotografie annotate manualmente su Roboflow**. Ho usato quel `best.pt` nella fase iniziale di riconoscimento e integrazione del tracking; successivamente ho proseguito l’addestramento sui dati sintetici preparati dai CAD.

Distinguo la preparazione manuale delle fotografie dalla generazione automatica dei render. Non attribuisco al primo run lo split, le epoche o le metriche del fine-tuning successivo. [Percorso di addestramento](ADDESTRAMENTO.md).

[Pagina principale](../README.md) · [UML e codice](UML_E_CODICE.md)
