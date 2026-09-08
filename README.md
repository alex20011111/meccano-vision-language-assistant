# Meccano Vision-Language Assistant

## Percezione RGB-D, tracking stabile e assistenza vocale per la composizione guidata

Repository del prototipo sviluppato nell'ambito di un tirocinio sull'interazione uomo-robot e l'integrazione di visione artificiale e modelli linguistici. Il sistema riconosce pezzi Meccano in plastica, ne stabilizza la classe nel tempo, genera una composizione con silhouette CAD e risponde a interrogazioni vocali sulla scena.

**Perimetro effettivamente implementato:** assistenza all'operatore con YOLO, ByteTrack, RealSense, geometria CAD e un LLM locale. Il codice disponibile non implementa attuazione robotica, nodi ROS/ROS2 o un VLM che riceva immagini direttamente.

### Comportamento della versione operativa

Ogni pressione di **G / Spazio** rigenera la composizione a partire dai pezzi riconosciuti a sinistra, senza controllare se il piano destro è libero e senza bloccare la rigenerazione di una figura già attiva. **N** richiede una nuova disposizione; **V / I** verifica i piazzamenti; **R** avvia la domanda vocale; **S** ferma la voce; **X** azzera la composizione senza azzerare il tracking.

La verifica dei singoli piazzamenti resta distinta dal controllo di occupazione del piano destro, che è stato rimosso. La raccolta dati sperimentale non fa parte del runtime.

### Classi e risultati

**A090 e A823 sono refusi di etichettatura, non pezzi reali.** Non devono essere presentate come classi fisiche né richiedono CAD o silhouette. A132 è il codice confermato dall'autore. A622 e A632 sono pezzi distinti.

I grafici forniti documentano un addestramento di 50 epoche e una validazione ricostruita come sintetica. Non costituiscono una misura del funzionamento sul banco reale o dell'efficacia dell'interazione uomo-robot. Il grafico AP per classe contiene incongruenze da verificare contro gli output numerici originali: non viene usato per certificare una graduatoria.

### Organizzazione della documentazione

La documentazione viene organizzata in un sito statico navigabile e in capitoli tecnici: contesto, evoluzione del progetto, pipeline offline/live/vocale, CAD e dataset, tracking, composizione, interazione vocale, risultati, catalogo dei moduli, installazione e limiti. Diagrammi di architettura, classi, sequenza, stati e distribuzione accompagnano le spiegazioni.

Pesi, dataset, STL, silhouette reali e conversazioni integrali non vengono redistribuiti. Le immagini del banco mancanti sono richieste all'autore, non ricostruite come evidenze fotografiche.
