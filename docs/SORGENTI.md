# Sorgenti Python

Ho organizzato il codice in otto moduli del programma e sette strumenti di preparazione. Il programma di riferimento mantiene il controllo del piano destro, il tracking continuo e l’arresto della voce.

## Primo modello

Il primo `best.pt` è stato ottenuto con un addestramento su **150 fotografie etichettate manualmente in Roboflow**. Successivamente ho preparato i dati sintetici dai CAD e proseguito l’addestramento dai pesi esistenti.

## Installazione e avvio

Pesi, silhouette, metadati, STL e configurazione del banco vanno conservati localmente. I comandi si eseguono dalla radice del repository.

```bash
python -m pip install -r requirements.txt
python meccano_tracker.py --model "percorso/best.pt" --silhouettes "percorso/silhouettes" --tracker "percorso/meccano_bytetrack.yaml" --no-voice
```

Per usare anche il microfono e la sintesi vocale, installare `requirements_voice.txt`, predisporre il modello locale configurato e togliere `--no-voice`. Gli strumenti CAD e BlenderProc richiedono i rispettivi ambienti software; non vengono eseguiti all’avvio del programma.

## Organizzazione

| File | Responsabilità |
|---|---|
| [meccano_tracker.py](../meccano_tracker.py) | Ingresso del programma, RealSense, inferenza, tracking e ciclo video. |
| [composition_controller.py](../composition_controller.py) | Composizione, controllo del piano destro e avviso di rientro. |
| [composition_ui.py](../composition_ui.py) | Pulsanti, pannelli e richiami visivi dei pezzi. |
| [assembly_guide_cad.py](../assembly_guide_cad.py) | Silhouette CAD, disposizione e verifica dei piazzamenti. |
| [part_orientation.py](../part_orientation.py) | Stima e stabilizzazione dell’orientamento sul piano. |
| [parts_catalog.py](../parts_catalog.py) | Descrizioni dei componenti e catalogo per il parsing vocale. |
| [voice_assistant.py](../voice_assistant.py) | Stato della scena, trascrizione, interpretazione e sintesi vocale. |
| [voice_runtime.py](../voice_runtime.py) | Processo vocale separato, cancellazione e arresto. |
| [crea_mappa.py](../crea_mappa.py) | Corrispondenze tra classi del checkpoint e file STL. |
| [genera_dataset_meccano.py](../genera_dataset_meccano.py) | Generazione delle scene sintetiche con BlenderProc. |
| [generate_silhouettes.py](../generate_silhouettes.py) | Proiezione e rasterizzazione delle sagome dai modelli STL. |
| [orient_and_generate.py](../orient_and_generate.py) | Orientamento manuale dei modelli prima della proiezione. |
| [prepara_addestramento.py](../prepara_addestramento.py) | Preparazione COCO/YOLO e augmentation del training set. |
| [prova_colori.py](../prova_colori.py) | Anteprima dei materiali e dei colori del rendering. |
| [rotate_silhouette.py](../rotate_silhouette.py) | Correzione dell’orientamento delle silhouette. |

## Lettura con UML

Le spiegazioni rimangono nella [guida UML e codice](UML_E_CODICE.md). Ho rimosso dai file Python i commenti esplicativi e le docstring descrittive, senza modificare algoritmi, parametri, prompt o messaggi dell’applicazione. Il testo del modulo usato dal comando `--help` è conservato.

La rimozione dei blocchi descrittivi ha modificato la numerazione delle righe. Gli intervalli nell’appendice HTML precedente si riferiscono alla copia di lettura documentata lì; l’indice seguente punta invece ai sorgenti pubblicati in questo ramo.

## Verifiche

La copia senza commenti è stata compilata e confrontata con la sintassi eseguibile della versione di riferimento, escludendo dal confronto i soli blocchi descrittivi. La suite offline comprende **124 test e 20 sottotest**, superati nell’esecuzione locale. Il riferimento di integrità del test su `ClassStabilizer` è aggiornato per tenere conto della rimozione delle docstring. Queste verifiche non sostituiscono le prove con camera, pesi, silhouette e audio del banco.

```bash
python -m pip install -r requirements_dev.txt
python -m pytest -q
```

## Indice delle implementazioni

### `meccano_tracker.py`

| Simbolo | Righe |
|---|---|
| `ClassStabilizer` | [L82–L215](../meccano_tracker.py#L82-L215) |
| `ClassStabilizer.__init__` | [L85–L102](../meccano_tracker.py#L85-L102) |
| `ClassStabilizer.update` | [L105–L140](../meccano_tracker.py#L105-L140) |
| `ClassStabilizer._try_inherit_from_ghost` | [L143–L165](../meccano_tracker.py#L143-L165) |
| `ClassStabilizer._weighted_majority` | [L168–L172](../meccano_tracker.py#L168-L172) |
| `ClassStabilizer.is_locked` | [L174–L175](../meccano_tracker.py#L174-L175) |
| `ClassStabilizer.forget` | [L178–L186](../meccano_tracker.py#L178-L186) |
| `ClassStabilizer.cleanup` | [L189–L215](../meccano_tracker.py#L189-L215) |
| `depth_at_bbox_center` | [L218–L229](../meccano_tracker.py#L218-L229) |
| `box_plausibile` | [L232–L249](../meccano_tracker.py#L232-L249) |
| `iou_xyxy` | [L252–L265](../meccano_tracker.py#L252-L265) |
| `deduplicate_detections` | [L268–L285](../meccano_tracker.py#L268-L285) |
| `RawDetectionSnapshot` | [L288–L318](../meccano_tracker.py#L288-L318) |
| `RawDetectionSnapshot.__init__` | [L291–L293](../meccano_tracker.py#L291-L293) |
| `RawDetectionSnapshot.reset` | [L295–L296](../meccano_tracker.py#L295-L296) |
| `RawDetectionSnapshot.__call__` | [L298–L318](../meccano_tracker.py#L298-L318) |
| `workspace_observations` | [L321–L406](../meccano_tracker.py#L321-L406) |
| `estimate_plane_z` | [L409–L418](../meccano_tracker.py#L409-L418) |
| `draw_detection` | [L421–L434](../meccano_tracker.py#L421-L434) |
| `draw_tracked_scene` | [L437–L449](../meccano_tracker.py#L437-L449) |
| `stop_voice` | [L460–L466](../meccano_tracker.py#L460-L466) |
| `dispatch_return_notice` | [L469–L478](../meccano_tracker.py#L469-L478) |
| `_arguments` | [L481–L491](../meccano_tracker.py#L481-L491) |
| `main` | [L494–L722](../meccano_tracker.py#L494-L722) |

### `composition_controller.py`

| Simbolo | Righe |
|---|---|
| `is_hand` | [L15–L16](../composition_controller.py#L15-L16) |
| `box_iou` | [L19–L25](../composition_controller.py#L19-L25) |
| `format_counts` | [L28–L29](../composition_controller.py#L28-L29) |
| `left_position` | [L32–L39](../composition_controller.py#L32-L39) |
| `ActionResult` | [L43–L45](../composition_controller.py#L43-L45) |
| `EmptyAreaGuard` | [L48–L80](../composition_controller.py#L48-L80) |
| `EmptyAreaGuard.__init__` | [L50–L61](../composition_controller.py#L50-L61) |
| `EmptyAreaGuard.observe` | [L63–L75](../composition_controller.py#L63-L75) |
| `EmptyAreaGuard.ready` | [L77–L80](../composition_controller.py#L77-L80) |
| `CompositionController` | [L83–L384](../composition_controller.py#L83-L384) |
| `CompositionController.__init__` | [L84–L110](../composition_controller.py#L84-L110) |
| `CompositionController._normalise` | [L113–L124](../composition_controller.py#L113-L124) |
| `CompositionController.observe` | [L126–L180](../composition_controller.py#L126-L180) |
| `CompositionController._valid_box` | [L183–L191](../composition_controller.py#L183-L191) |
| `CompositionController._add_right_blocker` | [L193–L206](../composition_controller.py#L193-L206) |
| `CompositionController._refresh_readiness_message` | [L208–L222](../composition_controller.py#L208-L222) |
| `CompositionController.inventory_ready` | [L225–L227](../composition_controller.py#L225-L227) |
| `CompositionController.readiness_reason` | [L229–L245](../composition_controller.py#L229-L245) |
| `CompositionController.generate` | [L247–L273](../composition_controller.py#L247-L273) |
| `CompositionController.finish` | [L275–L284](../composition_controller.py#L275-L284) |
| `CompositionController.check_completion` | [L286–L292](../composition_controller.py#L286-L292) |
| `CompositionController._update_return_warning` | [L294–L303](../composition_controller.py#L294-L303) |
| `CompositionController.return_warning` | [L307–L308](../composition_controller.py#L307-L308) |
| `CompositionController.take_return_announcement` | [L310–L315](../composition_controller.py#L310-L315) |
| `CompositionController.silence_return_announcement` | [L317–L319](../composition_controller.py#L317-L319) |
| `CompositionController._result` | [L321–L324](../composition_controller.py#L321-L324) |
| `CompositionController.toggle_verification` | [L326–L335](../composition_controller.py#L326-L335) |
| `CompositionController.report` | [L337–L363](../composition_controller.py#L337-L363) |
| `CompositionController.verification_text` | [L365–L384](../composition_controller.py#L365-L384) |

### `composition_ui.py`

| Simbolo | Righe |
|---|---|
| `put_text` | [L10–L13](../composition_ui.py#L10-L13) |
| `wrap_text` | [L16–L27](../composition_ui.py#L16-L27) |
| `draw_left_highlights` | [L30–L45](../composition_ui.py#L30-L45) |
| `draw_workspace_blockers` | [L48–L78](../composition_ui.py#L48-L78) |
| `workspace_status` | [L81–L90](../composition_ui.py#L81-L90) |
| `workspace_rows` | [L93–L117](../composition_ui.py#L93-L117) |
| `CompositionUI` | [L120–L265](../composition_ui.py#L120-L265) |
| `CompositionUI.__init__` | [L121–L127](../composition_ui.py#L121-L127) |
| `CompositionUI.open` | [L129–L131](../composition_ui.py#L129-L131) |
| `CompositionUI.mouse_callback` | [L133–L143](../composition_ui.py#L133-L143) |
| `CompositionUI.pop_actions` | [L145–L148](../composition_ui.py#L145-L148) |
| `CompositionUI.draw` | [L150–L207](../composition_ui.py#L150-L207) |
| `CompositionUI._draw_panel` | [L209–L256](../composition_ui.py#L209-L256) |
| `CompositionUI._draw_rows` | [L258–L265](../composition_ui.py#L258-L265) |

### `assembly_guide_cad.py`

| Simbolo | Righe |
|---|---|
| `SilhouetteLibrary` | [L51–L118](../assembly_guide_cad.py#L51-L118) |
| `SilhouetteLibrary.__init__` | [L54–L58](../assembly_guide_cad.py#L54-L58) |
| `SilhouetteLibrary._load_meta` | [L60–L76](../assembly_guide_cad.py#L60-L76) |
| `SilhouetteLibrary.has` | [L78–L79](../assembly_guide_cad.py#L78-L79) |
| `SilhouetteLibrary.get_image` | [L81–L100](../assembly_guide_cad.py#L81-L100) |
| `SilhouetteLibrary._crop_transparent_border` | [L103–L111](../assembly_guide_cad.py#L103-L111) |
| `SilhouetteLibrary.mm_per_px_native` | [L113–L118](../assembly_guide_cad.py#L113-L118) |
| `CadSlot` | [L121–L136](../assembly_guide_cad.py#L121-L136) |
| `CadSlot.__init__` | [L124–L133](../assembly_guide_cad.py#L124-L133) |
| `CadSlot.reset_progress` | [L135–L136](../assembly_guide_cad.py#L135-L136) |
| `CadAssemblyGuide` | [L139–L967](../assembly_guide_cad.py#L139-L967) |
| `CadAssemblyGuide.__init__` | [L142–L172](../assembly_guide_cad.py#L142-L172) |
| `CadAssemblyGuide.is_in_start_area` | [L175–L176](../assembly_guide_cad.py#L175-L176) |
| `CadAssemblyGuide.is_in_assembly_area` | [L178–L179](../assembly_guide_cad.py#L178-L179) |
| `CadAssemblyGuide.is_on_completed_slot` | [L181–L193](../assembly_guide_cad.py#L181-L193) |
| `CadAssemblyGuide.mm_to_px` | [L196–L201](../assembly_guide_cad.py#L196-L201) |
| `CadAssemblyGuide.part_size_mm` | [L204–L210](../assembly_guide_cad.py#L204-L210) |
| `CadAssemblyGuide.is_structural` | [L212–L217](../assembly_guide_cad.py#L212-L217) |
| `CadAssemblyGuide._obb_corners` | [L221–L234](../assembly_guide_cad.py#L221-L234) |
| `CadAssemblyGuide._obb_overlap` | [L237–L255](../assembly_guide_cad.py#L237-L255) |
| `CadAssemblyGuide._slot_obb` | [L257–L264](../assembly_guide_cad.py#L257-L264) |
| `CadAssemblyGuide._slot_mask` | [L266–L285](../assembly_guide_cad.py#L266-L285) |
| `CadAssemblyGuide._masks_overlap` | [L288–L303](../assembly_guide_cad.py#L288-L303) |
| `CadAssemblyGuide._snap_to_contact` | [L305–L347](../assembly_guide_cad.py#L305-L347) |
| `CadAssemblyGuide._separate_overlaps` | [L349–L386](../assembly_guide_cad.py#L349-L386) |
| `CadAssemblyGuide._figure_bbox` | [L389–L402](../assembly_guide_cad.py#L389-L402) |
| `CadAssemblyGuide._fit_into_assembly_area` | [L404–L427](../assembly_guide_cad.py#L404-L427) |
| `CadAssemblyGuide.generate_from_parts` | [L429–L487](../assembly_guide_cad.py#L429-L487) |
| `CadAssemblyGuide._layout_signature` | [L489–L492](../assembly_guide_cad.py#L489-L492) |
| `CadAssemblyGuide._jitter_figure` | [L494–L504](../assembly_guide_cad.py#L494-L504) |
| `CadAssemblyGuide._count_overlaps` | [L506–L514](../assembly_guide_cad.py#L506-L514) |
| `CadAssemblyGuide._print_final_report` | [L516–L541](../assembly_guide_cad.py#L516-L541) |
| `CadAssemblyGuide._build_figure` | [L543–L688](../assembly_guide_cad.py#L543-L688) |
| `CadAssemblyGuide._scaled_rotated_silhouette` | [L691–L727](../assembly_guide_cad.py#L691-L727) |
| `CadAssemblyGuide._overlay_bgra` | [L730–L753](../assembly_guide_cad.py#L730-L753) |
| `CadAssemblyGuide.update` | [L756–L780](../assembly_guide_cad.py#L756-L780) |
| `CadAssemblyGuide._match_distance` | [L782–L805](../assembly_guide_cad.py#L782-L805) |
| `CadAssemblyGuide._assign_parts` | [L807–L847](../assembly_guide_cad.py#L807-L847) |
| `CadAssemblyGuide._find_match` | [L849–L854](../assembly_guide_cad.py#L849-L854) |
| `CadAssemblyGuide._angle_diff` | [L857–L867](../assembly_guide_cad.py#L857-L867) |
| `CadAssemblyGuide._angle_diff_both` | [L870–L875](../assembly_guide_cad.py#L870-L875) |
| `CadAssemblyGuide.can_render` | [L878–L890](../assembly_guide_cad.py#L878-L890) |
| `CadAssemblyGuide.renderable` | [L892–L894](../assembly_guide_cad.py#L892-L894) |
| `CadAssemblyGuide.clear` | [L896–L906](../assembly_guide_cad.py#L896-L906) |
| `CadAssemblyGuide.progress` | [L909–L911](../assembly_guide_cad.py#L909-L911) |
| `CadAssemblyGuide.draw` | [L914–L967](../assembly_guide_cad.py#L914-L967) |

### `part_orientation.py`

| Simbolo | Righe |
|---|---|
| `estimate_angle_deg` | [L5–L56](../part_orientation.py#L5-L56) |
| `AngleSmoother` | [L59–L92](../part_orientation.py#L59-L92) |
| `AngleSmoother.__init__` | [L62–L65](../part_orientation.py#L62-L65) |
| `AngleSmoother.update` | [L67–L73](../part_orientation.py#L67-L73) |
| `AngleSmoother.get` | [L75–L86](../part_orientation.py#L75-L86) |
| `AngleSmoother.cleanup` | [L88–L92](../part_orientation.py#L88-L92) |

### `parts_catalog.py`

| Simbolo | Righe |
|---|---|
| `build_catalog_text` | [L245–L259](../parts_catalog.py#L245-L259) |

### `voice_assistant.py`

| Simbolo | Righe |
|---|---|
| `SceneState` | [L26–L62](../voice_assistant.py#L26-L62) |
| `SceneState.__init__` | [L29–L32](../voice_assistant.py#L29-L32) |
| `SceneState.update_part` | [L34–L41](../voice_assistant.py#L34-L41) |
| `SceneState.sync_with_active` | [L43–L47](../voice_assistant.py#L43-L47) |
| `SceneState.snapshot` | [L49–L51](../voice_assistant.py#L49-L51) |
| `SceneState.known_classes` | [L53–L56](../voice_assistant.py#L53-L56) |
| `SceneState.set_frame_shape` | [L58–L59](../voice_assistant.py#L58-L59) |
| `SceneState.get_frame_shape` | [L61–L62](../voice_assistant.py#L61-L62) |
| `_cm_to_words` | [L65–L68](../voice_assistant.py#L65-L68) |
| `describe_position` | [L71–L96](../voice_assistant.py#L71-L96) |
| `_words_to_number` | [L130–L157](../voice_assistant.py#L130-L157) |
| `VoiceAssistant` | [L160–L533](../voice_assistant.py#L160-L533) |
| `VoiceAssistant.__init__` | [L162–L169](../voice_assistant.py#L162-L169) |
| `VoiceAssistant.state` | [L172–L173](../voice_assistant.py#L172-L173) |
| `VoiceAssistant.last_error` | [L176–L177](../voice_assistant.py#L176-L177) |
| `VoiceAssistant._set_state` | [L179–L181](../voice_assistant.py#L179-L181) |
| `VoiceAssistant.is_busy` | [L183–L184](../voice_assistant.py#L183-L184) |
| `VoiceAssistant.trigger` | [L186–L187](../voice_assistant.py#L186-L187) |
| `VoiceAssistant.say_async` | [L189–L190](../voice_assistant.py#L189-L190) |
| `VoiceAssistant.stop` | [L192–L193](../voice_assistant.py#L192-L193) |
| `VoiceAssistant.cancel_tag` | [L195–L196](../voice_assistant.py#L195-L196) |
| `VoiceAssistant.close` | [L198–L199](../voice_assistant.py#L198-L199) |
| `VoiceAssistant._check_cancelled` | [L201–L203](../voice_assistant.py#L201-L203) |
| `VoiceAssistant._ensure_whisper` | [L205–L212](../voice_assistant.py#L205-L212) |
| `VoiceAssistant._run_pipeline` | [L215–L273](../voice_assistant.py#L215-L273) |
| `VoiceAssistant._build_answer` | [L276–L297](../voice_assistant.py#L276-L297) |
| `VoiceAssistant._describe_part_position` | [L299–L307](../voice_assistant.py#L299-L307) |
| `VoiceAssistant._short_hint` | [L309–L318](../voice_assistant.py#L309-L318) |
| `VoiceAssistant._spell_class` | [L321–L327](../voice_assistant.py#L321-L327) |
| `VoiceAssistant._extract_class` | [L330–L397](../voice_assistant.py#L330-L397) |
| `VoiceAssistant._disambiguate_by_letter` | [L399–L415](../voice_assistant.py#L399-L415) |
| `VoiceAssistant._extract_class_llama` | [L417–L467](../voice_assistant.py#L417-L467) |
| `VoiceAssistant._record_audio` | [L470–L484](../voice_assistant.py#L470-L484) |
| `VoiceAssistant._transcribe` | [L486–L496](../voice_assistant.py#L486-L496) |
| `VoiceAssistant._speak` | [L498–L533](../voice_assistant.py#L498-L533) |
| `_RemoteScene` | [L536–L553](../voice_assistant.py#L536-L553) |
| `_RemoteScene.__init__` | [L538–L540](../voice_assistant.py#L538-L540) |
| `_RemoteScene.snapshot` | [L542–L550](../voice_assistant.py#L542-L550) |
| `_RemoteScene.get_frame_shape` | [L552–L553](../voice_assistant.py#L552-L553) |
| `_voice_worker` | [L556–L592](../voice_assistant.py#L556-L592) |
| `_ordinal_it` | [L595–L599](../voice_assistant.py#L595-L599) |

### `voice_runtime.py`

| Simbolo | Righe |
|---|---|
| `VoiceCancelled` | [L6–L7](../voice_runtime.py#L6-L7) |
| `VoiceRuntime` | [L10–L202](../voice_runtime.py#L10-L202) |
| `VoiceRuntime.__init__` | [L11–L32](../voice_runtime.py#L11-L32) |
| `VoiceRuntime.state` | [L35–L37](../voice_runtime.py#L35-L37) |
| `VoiceRuntime.last_error` | [L40–L42](../voice_runtime.py#L40-L42) |
| `VoiceRuntime.is_busy` | [L44–L45](../voice_runtime.py#L44-L45) |
| `VoiceRuntime.submit` | [L47–L65](../voice_runtime.py#L47-L65) |
| `VoiceRuntime._request_stop_locked` | [L67–L77](../voice_runtime.py#L67-L77) |
| `VoiceRuntime.stop` | [L79–L86](../voice_runtime.py#L79-L86) |
| `VoiceRuntime.cancel_tag` | [L88–L102](../voice_runtime.py#L88-L102) |
| `VoiceRuntime._spawn_locked` | [L104–L118](../voice_runtime.py#L104-L118) |
| `VoiceRuntime._dispose_locked` | [L120–L130](../voice_runtime.py#L120-L130) |
| `VoiceRuntime._tick_locked` | [L132–L171](../voice_runtime.py#L132-L171) |
| `VoiceRuntime._supervise` | [L173–L187](../voice_runtime.py#L173-L187) |
| `VoiceRuntime.close` | [L189–L202](../voice_runtime.py#L189-L202) |

### `crea_mappa.py`

| Simbolo | Righe |
|---|---|
| `leggi_nomi` | [L15–L26](../crea_mappa.py#L15-L26) |
| `abbina` | [L29–L38](../crea_mappa.py#L29-L38) |
| `leggi_colori` | [L52–L72](../crea_mappa.py#L52-L72) |
| `main` | [L75–L174](../crea_mappa.py#L75-L174) |

### `genera_dataset_meccano.py`

| Simbolo | Righe |
|---|---|
| `carica_pezzi` | [L118–L175](../genera_dataset_meccano.py#L118-L175) |
| `piazza_mano` | [L291–L326](../genera_dataset_meccano.py#L291-L326) |
| `randomizza_materiale` | [L335–L359](../genera_dataset_meccano.py#L335-L359) |
| `posa_camera` | [L362–L371](../genera_dataset_meccano.py#L362-L371) |
| `pulisci_coco` | [L497–L544](../genera_dataset_meccano.py#L497-L544) |

### `generate_silhouettes.py`

| Simbolo | Righe |
|---|---|
| `auto_flatten` | [L17–L38](../generate_silhouettes.py#L17-L38) |
| `mesh_outline_polygon` | [L41–L65](../generate_silhouettes.py#L41-L65) |
| `rasterize_polygon` | [L68–L85](../generate_silhouettes.py#L68-L85) |
| `mask_to_rgba` | [L88–L93](../generate_silhouettes.py#L88-L93) |
| `main` | [L96–L151](../generate_silhouettes.py#L96-L151) |

### `orient_and_generate.py`

| Simbolo | Righe |
|---|---|
| `rot_matrix` | [L21–L36](../orient_and_generate.py#L21-L36) |
| `mesh_outline_polygon` | [L39–L64](../orient_and_generate.py#L39-L64) |
| `rasterize_polygon` | [L67–L84](../orient_and_generate.py#L67-L84) |
| `mask_to_rgba` | [L87–L92](../orient_and_generate.py#L87-L92) |
| `generate_one` | [L95–L106](../orient_and_generate.py#L95-L106) |
| `load_meta` | [L109–L114](../orient_and_generate.py#L109-L114) |
| `save_meta` | [L117–L119](../orient_and_generate.py#L117-L119) |
| `main` | [L122–L194](../orient_and_generate.py#L122-L194) |

### `prepara_addestramento.py`

| Simbolo | Righe |
|---|---|
| `bbox_valide` | [L61–L78](../prepara_addestramento.py#L61-L78) |
| `scrivi_yolo` | [L108–L117](../prepara_addestramento.py#L108-L117) |
| `copia_originale` | [L120–L126](../prepara_addestramento.py#L120-L126) |

### `prova_colori.py`

| Simbolo | Righe |
|---|---|

### `rotate_silhouette.py`

| Simbolo | Righe |
|---|---|
| `load_meta` | [L11–L16](../rotate_silhouette.py#L11-L16) |
| `save_meta` | [L19–L22](../rotate_silhouette.py#L19-L22) |
| `rotate_png` | [L25–L64](../rotate_silhouette.py#L25-L64) |
| `main` | [L67–L98](../rotate_silhouette.py#L67-L98) |
