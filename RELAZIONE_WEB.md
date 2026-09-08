# Relazione web del progetto

La relazione HTML è sviluppata nel ramo [`docs/navigable-project-report`](https://github.com/alex20011111/meccano-vision-language-assistant/tree/docs/navigable-project-report/report), senza sovrascrivere le modifiche al runtime in corso su `main`.

## Consultazione

- [Sorgente della pagina HTML](https://github.com/alex20011111/meccano-vision-language-assistant/blob/docs/navigable-project-report/report/index.html)
- [Confronto e revisione delle modifiche](https://github.com/alex20011111/meccano-vision-language-assistant/compare/main...docs/navigable-project-report)
- [Workflow di pubblicazione](https://github.com/alex20011111/meccano-vision-language-assistant/actions/workflows/publish-navigable-report.yml)

Il workflow prepara il sito da `report/`, controlla ancore e sintassi JavaScript, raccoglie le figure originali disponibili e tenta la pubblicazione con GitHub Pages. **L'esistenza dei sorgenti non equivale a un deploy riuscito:** consultare l'esito del workflow. Se l'attivazione automatica di Pages non è consentita al token del workflow, il proprietario deve abilitare GitHub Pages con sorgente GitHub Actions nelle impostazioni del repository.

## Percorso di lettura

La pagina copre problema e obiettivi, evoluzione delle scelte, pipeline offline e online, componenti, viste UML, tracking, geometria CAD, voce, dataset, moduli, lettura degli undici grafici, guida operativa, riproducibilità, limiti, materiale fotografico e glossario.

Navigazione con indice, ricerca, filtri, ingrandimento delle figure, tema chiaro/scuro e stampa. I diagrammi sono SVG incorporati, senza dipendenza da un servizio esterno per il rendering.

## Tassonomia e interpretazione dei risultati

A090 e A823 sono refusi di etichettatura, non pezzi fisici. A132 è confermato; A622 e A632 sono distinti; Hand è ausiliaria. Le PNG di addestramento rimangono inalterate. Il grafico AP per classe viene segnalato come da verificare, non usato come graduatoria certificata. Le metriche del detector non vengono presentate come prestazioni del tracking, della voce o di uno studio HRI.

## Materiale ancora richiesto

Foto reale del banco e della RealSense, schermata della composizione attuale e schermata della verifica con tracking visibile. Per una verifica numerica dei risultati servono anche gli output originali del run e dell'esportazione per classe. Gli export integrali delle conversazioni non vengono pubblicati.

## Requisito operativo da allineare

La richiesta visibile nella conversazione prescrive G libero a ogni pressione senza controllo del piano destro. Il documento `docs/DECISIONS.md` su main descrive una politica differente. Il contributo di documentazione non decide silenziosamente questa divergenza e non riscrive il runtime.
