# Meccano Vision-Language Assistant

## Percezione RGB-D, tracking stabile e assistenza vocale al montaggio

Durante il tirocinio ho sviluppato un assistente visivo e vocale per un banco di componenti Meccano. Sono partito dal riconoscimento dei pezzi con YOLO e ho lavorato sulla continuità dell’informazione: seguire un componente mentre viene spostato, mantenerne stabile la classe e usare la sua posizione per aiutare l’operatore.

Il sistema combina una camera RGB-D RealSense, YOLO, ByteTrack, uno stabilizzatore delle classi, silhouette ricavate dai CAD e un’interfaccia vocale con un modello linguistico locale. Il risultato è un prototipo di assistenza all’operatore; non comprende l’attuazione di un robot, nodi ROS/ROS2 o un VLM che riceva direttamente le immagini.

## Dal primo modello al fine-tuning

**Il primo `best.pt` è stato ottenuto con un addestramento basato su 150 fotografie, che ho etichettato manualmente su Roboflow.** Questa è la fase iniziale del riconoscimento dei componenti, precedente alla generazione del dataset sintetico. Roboflow è stato utilizzato per l’annotazione delle immagini: non identifico la piattaforma di annotazione con l’ambiente in cui è stato eseguito il training.

Da quel modello sono partito per integrare il tracking e la stabilizzazione. In seguito ho utilizzato i CAD per generare scene sintetiche, preparato le annotazioni in formato YOLO e proseguito l’addestramento dai pesi esistenti. Distinguo quindi il **primo addestramento sulle 150 fotografie** dal **successivo fine-tuning sui dati sintetici**. I grafici della relazione riguardano la fase successiva e non misurano retroattivamente le prestazioni del primo modello.

[Storia del modello e preparazione dei dati](docs/ADDESTRAMENTO.md)

## Come funziona

```text
Camera RGB-D → YOLO → ByteTrack → stabilizzazione della classe
                                      ↓
                               stato della scena
                                 ↙          ↘
                      guida con sagome     assistente vocale
                      e piazzamenti       testo → codice → posizione
```

Ho separato la percezione dall’interpretazione linguistica. Il modello linguistico interpreta la descrizione del pezzo usando il catalogo; la selezione delle istanze e la costruzione della risposta di posizione rimangono in Python. La voce lavora in un processo locale separato dal ciclo video.

## Comandi del banco

| Comando | Funzione |
|---|---|
| **G / Spazio** | Avvia una composizione dai pezzi riconosciuti stabilmente a sinistra, con il piano destro libero. Non sostituisce una composizione già attiva. |
| **N** | Richiede una nuova disposizione quando il controllo del piano destro lo consente. |
| **V / I** | Mostra o nasconde il riepilogo e i richiami dei pezzi da prendere sul piano sinistro. |
| **R** | Avvia una domanda vocale per codice o descrizione. |
| **S** | Interrompe la richiesta vocale corrente senza fermare la camera o il tracking. |
| **X** | Azzera la composizione, mantiene il tracking e controlla il rientro dei pezzi. |

Ho mantenuto il **controllo del piano destro attivo** nella versione di riferimento `meccano_fix_piano_destro`. La verifica dei singoli piazzamenti sulle sagome è un controllo distinto e continua durante il lavoro. Dopo X o al completamento, la presenza di pezzi nella zona di montaggio attiva l’avviso «RIPORTARE I PEZZI NEL PIANO DI PARTENZA».

La raccolta dati sperimentale non fa parte del funzionamento corrente.

## Documentazione

- [UML e codice: percorso sequenziale, classi, chiamate e sorgenti](docs/UML_E_CODICE.md)
- [Scelte progettuali e versione di riferimento](docs/DECISIONS.md)
- [Consultazione della relazione HTML](RELAZIONE_WEB.md)

Nella sezione UML seguo i dati dalla preparazione offline alla chiusura del programma. Per ogni modulo descrivo responsabilità, ingressi, uscite e collegamenti con gli altri componenti. I riferimenti di riga riguardano le copie dei sorgenti identificate nell’appendice tecnica; non presuppongono che tutti i file del banco siano presenti nel ramo principale.

## Classi e risultati

**A090 e A823 sono errori che ho introdotto durante l’etichettatura: non corrispondono a pezzi reali.** A132 è il codice corretto del perno; A622 e A632 sono componenti distinti. Hand è una classe ausiliaria, non un pezzo della composizione. Mantengo distinta la tassonomia fisica dall’ordine degli indici dei checkpoint, che non va modificato senza aggiornare coerentemente le annotazioni.

I grafici riportano 50 epoche del training successivo e una validazione sintetica. Li uso per discutere la convergenza del detector, non come misura del tracking, della risposta vocale o dell’efficacia dell’interazione sul banco. Il grafico AP per classe presenta incongruenze rispetto alla tassonomia e alle matrici di confusione; prima di utilizzarlo per un confronto fra componenti devo verificarne la corrispondenza fra nomi e valori.

## Risorse per la riproduzione

Pesi, fotografie del dataset iniziale, dataset sintetico, STL, silhouette e configurazione del banco non sono inclusi nel repository. Le immagini della relazione illustrano il dispositivo e il funzionamento del prototipo, ma non sostituiscono questi asset. Mantengo separati i risultati di addestramento, le verifiche software e le prove con camera e audio reali.
