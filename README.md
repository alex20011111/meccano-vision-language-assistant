# Meccano Vision-Language Assistant

## Percezione RGB-D, tracking stabile e assistenza vocale per la composizione guidata

Repository del prototipo sviluppato nell'ambito di un tirocinio sull'interazione uomo-robot e l'integrazione di visione artificiale e modelli linguistici. Il sistema riconosce pezzi Meccano in plastica, ne stabilizza la classe nel tempo, genera una composizione con silhouette CAD e risponde a interrogazioni vocali sulla scena.

**Perimetro effettivamente implementato:** assistenza all'operatore con YOLO, ByteTrack, RealSense, geometria CAD e un LLM locale. I sorgenti di riferimento forniti nella conversazione non implementano attuazione robotica, nodi ROS/ROS2 o un VLM che riceva immagini direttamente.

### UML e codice — lettura guidata

**[Apri la guida tecnica: UML, sequenza di esecuzione e responsabilità dei moduli](docs/UML_E_CODICE.md)**

La guida segue i dati dal catalogo e dai CAD al dataset, poi dal frame RGB-D al tracking, alla composizione e alla risposta vocale. Collega spiegazioni e UML ai nomi reali delle implementazioni e distingue i commenti storici dal comportamento del codice.

Nella conversazione è disponibile anche **`Meccano_Relazione_UML_Codice.html`**, copia locale navigabile con 15 file, 217 schede di classi/funzioni/metodi, 33 blocchi a livello modulo, sorgenti numerati e nove diagrammi cliccabili. **La guida Markdown è pubblicata qui; la presenza di questo collegamento non equivale al caricamento del file HTML completo o a un deployment GitHub Pages.** I riferimenti ai sorgenti sono esplicitamente associati al pacchetto di baseline e agli allegati, non a file implicitamente presenti su main.

### Comportamento della versione di riferimento

**Precisazione dell'autore recepita:** la baseline è `meccano_fix_piano_destro.zip`, con **controllo del piano destro attivo**. La richiesta intermedia di eliminarlo è superata. Questo testo sostituisce la precedente descrizione di G come rigenerazione incondizionata; non costituisce una modifica del runtime sul banco.

**G / Spazio** avvia una composizione con i pezzi riconosciuti stabilmente a sinistra, rispettando i prerequisiti del piano libero; non rigenera una figura già attiva. **N** richiede una nuova disposizione soltanto quando il controllo lo consente. **V / I** mostra o nasconde il riepilogo e i richiami dei pezzi da prendere a sinistra; la verifica geometrica dei piazzamenti continua. **R** avvia la domanda vocale; **S** ferma il processo vocale locale; **X** azzera la composizione senza azzerare il tracking e attiva il controllo di rientro.

La verifica dei singoli piazzamenti è distinta dal controllo di occupazione del piano destro. La raccolta dati sperimentale non fa parte della baseline operativa.

### Classi e risultati

**A090 e A823 sono refusi di etichettatura, non pezzi reali.** Non devono essere presentate come classi fisiche né richiedono CAD o silhouette. A132 è il codice confermato dall'autore. A622 e A632 sono pezzi distinti. La guida segnala dove questi requisiti non sono ancora completamente rappresentati nei sorgenti della baseline, senza fingere correzioni applicate.

I grafici forniti documentano un addestramento di 50 epoche e una validazione ricostruita come sintetica. Non costituiscono una misura del funzionamento sul banco reale o dell'efficacia dell'interazione uomo-robot. Il grafico AP per classe contiene incongruenze da verificare contro gli output numerici originali: non viene usato per certificare una graduatoria.

### Organizzazione della documentazione

La documentazione comprende contesto, evoluzione del progetto, pipeline offline/live/vocale, CAD e dataset, tracking, composizione, interazione vocale, risultati, catalogo dei moduli, installazione e limiti. La [sezione UML e codice](docs/UML_E_CODICE.md) aggiunge il percorso sequenziale e la lettura delle implementazioni effettivamente disponibili.

Pesi, dataset, STL, silhouette reali e conversazioni integrali non vengono redistribuiti. Le immagini del banco mancanti sono richieste all'autore, non ricostruite come evidenze fotografiche.
