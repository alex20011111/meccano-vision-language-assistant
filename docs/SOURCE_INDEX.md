# Source index

The entries below refer to the English files published in this repository.

## meccano_tracker.py

I use this module to start and coordinate the camera, detector, tracking memory, guide, interface and commands.

| Symbol | Kind | Lines |
|---|---|---|
| `ClassStabilizer` | class | [76–209](../meccano_tracker.py#L76-L209) |
| `ClassStabilizer.__init__` | function/method | [79–96](../meccano_tracker.py#L79-L96) |
| `ClassStabilizer.update` | function/method | [99–134](../meccano_tracker.py#L99-L134) |
| `ClassStabilizer._try_inherit_from_ghost` | function/method | [137–159](../meccano_tracker.py#L137-L159) |
| `ClassStabilizer._weighted_majority` | function/method | [162–166](../meccano_tracker.py#L162-L166) |
| `ClassStabilizer.is_locked` | function/method | [168–169](../meccano_tracker.py#L168-L169) |
| `ClassStabilizer.forget` | function/method | [172–180](../meccano_tracker.py#L172-L180) |
| `ClassStabilizer.cleanup` | function/method | [183–209](../meccano_tracker.py#L183-L209) |
| `depth_at_bbox_center` | function/method | [212–223](../meccano_tracker.py#L212-L223) |
| `box_plausibile` | function/method | [226–243](../meccano_tracker.py#L226-L243) |
| `iou_xyxy` | function/method | [246–259](../meccano_tracker.py#L246-L259) |
| `deduplicate_detections` | function/method | [262–279](../meccano_tracker.py#L262-L279) |
| `deduplicate_detections.sort_key` | function/method | [265–270](../meccano_tracker.py#L265-L270) |
| `RawDetectionSnapshot` | class | [282–312](../meccano_tracker.py#L282-L312) |
| `RawDetectionSnapshot.__init__` | function/method | [285–287](../meccano_tracker.py#L285-L287) |
| `RawDetectionSnapshot.reset` | function/method | [289–290](../meccano_tracker.py#L289-L290) |
| `RawDetectionSnapshot.__call__` | function/method | [292–312](../meccano_tracker.py#L292-L312) |
| `workspace_observations` | function/method | [315–400](../meccano_tracker.py#L315-L400) |
| `workspace_observations.reject` | function/method | [329–331](../meccano_tracker.py#L329-L331) |
| `workspace_observations.geometry` | function/method | [333–359](../meccano_tracker.py#L333-L359) |
| `estimate_plane_z` | function/method | [403–412](../meccano_tracker.py#L403-L412) |
| `draw_detection` | function/method | [415–428](../meccano_tracker.py#L415-L428) |
| `draw_tracked_scene` | function/method | [431–443](../meccano_tracker.py#L431-L443) |
| `stop_voice` | function/method | [454–460](../meccano_tracker.py#L454-L460) |
| `dispatch_return_notice` | function/method | [463–472](../meccano_tracker.py#L463-L472) |
| `_arguments` | function/method | [475–485](../meccano_tracker.py#L475-L485) |
| `main` | function/method | [488–716](../meccano_tracker.py#L488-L716) |

## composition_controller.py

I separated composition rules from drawing so that inventory, start, change, reporting and part return do not depend on the video window.

| Symbol | Kind | Lines |
|---|---|---|
| `is_hand` | function/method | [15–16](../composition_controller.py#L15-L16) |
| `box_iou` | function/method | [19–25](../composition_controller.py#L19-L25) |
| `format_counts` | function/method | [28–29](../composition_controller.py#L28-L29) |
| `left_position` | function/method | [32–39](../composition_controller.py#L32-L39) |
| `ActionResult` | class | [42–45](../composition_controller.py#L42-L45) |
| `EmptyAreaGuard` | class | [48–80](../composition_controller.py#L48-L80) |
| `EmptyAreaGuard.__init__` | function/method | [50–61](../composition_controller.py#L50-L61) |
| `EmptyAreaGuard.observe` | function/method | [63–75](../composition_controller.py#L63-L75) |
| `EmptyAreaGuard.ready` | function/method | [77–80](../composition_controller.py#L77-L80) |
| `CompositionController` | class | [83–384](../composition_controller.py#L83-L384) |
| `CompositionController.__init__` | function/method | [84–110](../composition_controller.py#L84-L110) |
| `CompositionController._normalise` | function/method | [112–124](../composition_controller.py#L112-L124) |
| `CompositionController.observe` | function/method | [126–180](../composition_controller.py#L126-L180) |
| `CompositionController._valid_box` | function/method | [182–191](../composition_controller.py#L182-L191) |
| `CompositionController._add_right_blocker` | function/method | [193–206](../composition_controller.py#L193-L206) |
| `CompositionController._refresh_readiness_message` | function/method | [208–222](../composition_controller.py#L208-L222) |
| `CompositionController.inventory_ready` | function/method | [224–227](../composition_controller.py#L224-L227) |
| `CompositionController.readiness_reason` | function/method | [229–245](../composition_controller.py#L229-L245) |
| `CompositionController.generate` | function/method | [247–273](../composition_controller.py#L247-L273) |
| `CompositionController.finish` | function/method | [275–284](../composition_controller.py#L275-L284) |
| `CompositionController.check_completion` | function/method | [286–292](../composition_controller.py#L286-L292) |
| `CompositionController._update_return_warning` | function/method | [294–303](../composition_controller.py#L294-L303) |
| `CompositionController.return_warning` | function/method | [306–308](../composition_controller.py#L306-L308) |
| `CompositionController.take_return_announcement` | function/method | [310–315](../composition_controller.py#L310-L315) |
| `CompositionController.silence_return_announcement` | function/method | [317–319](../composition_controller.py#L317-L319) |
| `CompositionController._result` | function/method | [321–324](../composition_controller.py#L321-L324) |
| `CompositionController.toggle_verification` | function/method | [326–335](../composition_controller.py#L326-L335) |
| `CompositionController.report` | function/method | [337–363](../composition_controller.py#L337-L363) |
| `CompositionController.verification_text` | function/method | [365–384](../composition_controller.py#L365-L384) |

## assembly_guide_cad.py

I use the CAD guide to turn the available parts into silhouette targets and assign each observed instance to at most one target.

| Symbol | Kind | Lines |
|---|---|---|
| `SilhouetteLibrary` | class | [51–118](../assembly_guide_cad.py#L51-L118) |
| `SilhouetteLibrary.__init__` | function/method | [54–58](../assembly_guide_cad.py#L54-L58) |
| `SilhouetteLibrary._load_meta` | function/method | [60–76](../assembly_guide_cad.py#L60-L76) |
| `SilhouetteLibrary.has` | function/method | [78–79](../assembly_guide_cad.py#L78-L79) |
| `SilhouetteLibrary.get_image` | function/method | [81–100](../assembly_guide_cad.py#L81-L100) |
| `SilhouetteLibrary._crop_transparent_border` | function/method | [102–111](../assembly_guide_cad.py#L102-L111) |
| `SilhouetteLibrary.mm_per_px_native` | function/method | [113–118](../assembly_guide_cad.py#L113-L118) |
| `CadSlot` | class | [121–136](../assembly_guide_cad.py#L121-L136) |
| `CadSlot.__init__` | function/method | [124–133](../assembly_guide_cad.py#L124-L133) |
| `CadSlot.reset_progress` | function/method | [135–136](../assembly_guide_cad.py#L135-L136) |
| `CadAssemblyGuide` | class | [139–967](../assembly_guide_cad.py#L139-L967) |
| `CadAssemblyGuide.__init__` | function/method | [142–172](../assembly_guide_cad.py#L142-L172) |
| `CadAssemblyGuide.is_in_start_area` | function/method | [175–176](../assembly_guide_cad.py#L175-L176) |
| `CadAssemblyGuide.is_in_assembly_area` | function/method | [178–179](../assembly_guide_cad.py#L178-L179) |
| `CadAssemblyGuide.is_on_completed_slot` | function/method | [181–193](../assembly_guide_cad.py#L181-L193) |
| `CadAssemblyGuide.mm_to_px` | function/method | [196–201](../assembly_guide_cad.py#L196-L201) |
| `CadAssemblyGuide.part_size_mm` | function/method | [204–210](../assembly_guide_cad.py#L204-L210) |
| `CadAssemblyGuide.is_structural` | function/method | [212–217](../assembly_guide_cad.py#L212-L217) |
| `CadAssemblyGuide._obb_corners` | function/method | [220–234](../assembly_guide_cad.py#L220-L234) |
| `CadAssemblyGuide._obb_overlap` | function/method | [236–255](../assembly_guide_cad.py#L236-L255) |
| `CadAssemblyGuide._slot_obb` | function/method | [257–264](../assembly_guide_cad.py#L257-L264) |
| `CadAssemblyGuide._slot_mask` | function/method | [266–285](../assembly_guide_cad.py#L266-L285) |
| `CadAssemblyGuide._masks_overlap` | function/method | [287–303](../assembly_guide_cad.py#L287-L303) |
| `CadAssemblyGuide._snap_to_contact` | function/method | [305–347](../assembly_guide_cad.py#L305-L347) |
| `CadAssemblyGuide._separate_overlaps` | function/method | [349–386](../assembly_guide_cad.py#L349-L386) |
| `CadAssemblyGuide._figure_bbox` | function/method | [389–402](../assembly_guide_cad.py#L389-L402) |
| `CadAssemblyGuide._fit_into_assembly_area` | function/method | [404–427](../assembly_guide_cad.py#L404-L427) |
| `CadAssemblyGuide.generate_from_parts` | function/method | [429–487](../assembly_guide_cad.py#L429-L487) |
| `CadAssemblyGuide._layout_signature` | function/method | [489–492](../assembly_guide_cad.py#L489-L492) |
| `CadAssemblyGuide._jitter_figure` | function/method | [494–504](../assembly_guide_cad.py#L494-L504) |
| `CadAssemblyGuide._count_overlaps` | function/method | [506–514](../assembly_guide_cad.py#L506-L514) |
| `CadAssemblyGuide._print_final_report` | function/method | [516–541](../assembly_guide_cad.py#L516-L541) |
| `CadAssemblyGuide._build_figure` | function/method | [543–688](../assembly_guide_cad.py#L543-L688) |
| `CadAssemblyGuide._build_figure.add_anchors` | function/method | [589–597](../assembly_guide_cad.py#L589-L597) |
| `CadAssemblyGuide._scaled_rotated_silhouette` | function/method | [691–727](../assembly_guide_cad.py#L691-L727) |
| `CadAssemblyGuide._overlay_bgra` | function/method | [730–753](../assembly_guide_cad.py#L730-L753) |
| `CadAssemblyGuide.update` | function/method | [756–780](../assembly_guide_cad.py#L756-L780) |
| `CadAssemblyGuide._match_distance` | function/method | [782–805](../assembly_guide_cad.py#L782-L805) |
| `CadAssemblyGuide._assign_parts` | function/method | [807–847](../assembly_guide_cad.py#L807-L847) |
| `CadAssemblyGuide._assign_parts.assign` | function/method | [828–841](../assembly_guide_cad.py#L828-L841) |
| `CadAssemblyGuide._find_match` | function/method | [849–854](../assembly_guide_cad.py#L849-L854) |
| `CadAssemblyGuide._angle_diff` | function/method | [856–867](../assembly_guide_cad.py#L856-L867) |
| `CadAssemblyGuide._angle_diff.diff_mod180` | function/method | [860–862](../assembly_guide_cad.py#L860-L862) |
| `CadAssemblyGuide._angle_diff_both` | function/method | [869–875](../assembly_guide_cad.py#L869-L875) |
| `CadAssemblyGuide._angle_diff_both.dm` | function/method | [872–874](../assembly_guide_cad.py#L872-L874) |
| `CadAssemblyGuide.can_render` | function/method | [878–890](../assembly_guide_cad.py#L878-L890) |
| `CadAssemblyGuide.renderable` | function/method | [892–894](../assembly_guide_cad.py#L892-L894) |
| `CadAssemblyGuide.clear` | function/method | [896–906](../assembly_guide_cad.py#L896-L906) |
| `CadAssemblyGuide.progress` | function/method | [909–911](../assembly_guide_cad.py#L909-L911) |
| `CadAssemblyGuide.draw` | function/method | [914–967](../assembly_guide_cad.py#L914-L967) |

## part_orientation.py

I estimate direction from the part shape in its RGB crop and smooth it across frames.

| Symbol | Kind | Lines |
|---|---|---|
| `estimate_angle_deg` | function/method | [5–56](../part_orientation.py#L5-L56) |
| `AngleSmoother` | class | [59–92](../part_orientation.py#L59-L92) |
| `AngleSmoother.__init__` | function/method | [62–65](../part_orientation.py#L62-L65) |
| `AngleSmoother.update` | function/method | [67–73](../part_orientation.py#L67-L73) |
| `AngleSmoother.get` | function/method | [75–86](../part_orientation.py#L75-L86) |
| `AngleSmoother.cleanup` | function/method | [88–92](../part_orientation.py#L88-L92) |

## composition_ui.py

I keep buttons, panels and visual cues here, separate from the controller's decisions.

| Symbol | Kind | Lines |
|---|---|---|
| `put_text` | function/method | [10–13](../composition_ui.py#L10-L13) |
| `wrap_text` | function/method | [16–27](../composition_ui.py#L16-L27) |
| `draw_left_highlights` | function/method | [30–45](../composition_ui.py#L30-L45) |
| `draw_workspace_blockers` | function/method | [48–78](../composition_ui.py#L48-L78) |
| `workspace_status` | function/method | [81–90](../composition_ui.py#L81-L90) |
| `workspace_rows` | function/method | [93–117](../composition_ui.py#L93-L117) |
| `CompositionUI` | class | [120–265](../composition_ui.py#L120-L265) |
| `CompositionUI.__init__` | function/method | [121–127](../composition_ui.py#L121-L127) |
| `CompositionUI.open` | function/method | [129–131](../composition_ui.py#L129-L131) |
| `CompositionUI.mouse_callback` | function/method | [133–143](../composition_ui.py#L133-L143) |
| `CompositionUI.pop_actions` | function/method | [145–148](../composition_ui.py#L145-L148) |
| `CompositionUI.draw` | function/method | [150–207](../composition_ui.py#L150-L207) |
| `CompositionUI._draw_panel` | function/method | [209–256](../composition_ui.py#L209-L256) |
| `CompositionUI._draw_rows` | function/method | [258–265](../composition_ui.py#L258-L265) |

## voice_assistant.py

I separate request interpretation from instance selection: the language model resolves a description, while Python reads the scene and constructs the answer.

| Symbol | Kind | Lines |
|---|---|---|
| `SceneState` | class | [26–62](../voice_assistant.py#L26-L62) |
| `SceneState.__init__` | function/method | [29–32](../voice_assistant.py#L29-L32) |
| `SceneState.update_part` | function/method | [34–41](../voice_assistant.py#L34-L41) |
| `SceneState.sync_with_active` | function/method | [43–47](../voice_assistant.py#L43-L47) |
| `SceneState.snapshot` | function/method | [49–51](../voice_assistant.py#L49-L51) |
| `SceneState.known_classes` | function/method | [53–56](../voice_assistant.py#L53-L56) |
| `SceneState.set_frame_shape` | function/method | [58–59](../voice_assistant.py#L58-L59) |
| `SceneState.get_frame_shape` | function/method | [61–62](../voice_assistant.py#L61-L62) |
| `_cm_to_words` | function/method | [65–68](../voice_assistant.py#L65-L68) |
| `describe_position` | function/method | [71–96](../voice_assistant.py#L71-L96) |
| `_words_to_number` | function/method | [124–138](../voice_assistant.py#L124-L138) |
| `VoiceAssistant` | class | [141–514](../voice_assistant.py#L141-L514) |
| `VoiceAssistant.__init__` | function/method | [143–150](../voice_assistant.py#L143-L150) |
| `VoiceAssistant.state` | function/method | [152–154](../voice_assistant.py#L152-L154) |
| `VoiceAssistant.last_error` | function/method | [156–158](../voice_assistant.py#L156-L158) |
| `VoiceAssistant._set_state` | function/method | [160–162](../voice_assistant.py#L160-L162) |
| `VoiceAssistant.is_busy` | function/method | [164–165](../voice_assistant.py#L164-L165) |
| `VoiceAssistant.trigger` | function/method | [167–168](../voice_assistant.py#L167-L168) |
| `VoiceAssistant.say_async` | function/method | [170–171](../voice_assistant.py#L170-L171) |
| `VoiceAssistant.stop` | function/method | [173–174](../voice_assistant.py#L173-L174) |
| `VoiceAssistant.cancel_tag` | function/method | [176–177](../voice_assistant.py#L176-L177) |
| `VoiceAssistant.close` | function/method | [179–180](../voice_assistant.py#L179-L180) |
| `VoiceAssistant._check_cancelled` | function/method | [182–184](../voice_assistant.py#L182-L184) |
| `VoiceAssistant._ensure_whisper` | function/method | [186–193](../voice_assistant.py#L186-L193) |
| `VoiceAssistant._run_pipeline` | function/method | [196–254](../voice_assistant.py#L196-L254) |
| `VoiceAssistant._build_answer` | function/method | [257–278](../voice_assistant.py#L257-L278) |
| `VoiceAssistant._describe_part_position` | function/method | [280–288](../voice_assistant.py#L280-L288) |
| `VoiceAssistant._short_hint` | function/method | [290–299](../voice_assistant.py#L290-L299) |
| `VoiceAssistant._spell_class` | function/method | [302–308](../voice_assistant.py#L302-L308) |
| `VoiceAssistant._extract_class` | function/method | [311–378](../voice_assistant.py#L311-L378) |
| `VoiceAssistant._disambiguate_by_letter` | function/method | [380–396](../voice_assistant.py#L380-L396) |
| `VoiceAssistant._extract_class_llama` | function/method | [398–448](../voice_assistant.py#L398-L448) |
| `VoiceAssistant._record_audio` | function/method | [451–465](../voice_assistant.py#L451-L465) |
| `VoiceAssistant._transcribe` | function/method | [467–477](../voice_assistant.py#L467-L477) |
| `VoiceAssistant._speak` | function/method | [479–514](../voice_assistant.py#L479-L514) |
| `_RemoteScene` | class | [517–534](../voice_assistant.py#L517-L534) |
| `_RemoteScene.__init__` | function/method | [519–521](../voice_assistant.py#L519-L521) |
| `_RemoteScene.snapshot` | function/method | [523–531](../voice_assistant.py#L523-L531) |
| `_RemoteScene.get_frame_shape` | function/method | [533–534](../voice_assistant.py#L533-L534) |
| `_voice_worker` | function/method | [537–573](../voice_assistant.py#L537-L573) |
| `_ordinal_it` | function/method | [576–580](../voice_assistant.py#L576-L580) |

## voice_runtime.py

I isolate voice work in a controllable process so it can be stopped without blocking video.

| Symbol | Kind | Lines |
|---|---|---|
| `VoiceCancelled` | class | [6–7](../voice_runtime.py#L6-L7) |
| `VoiceRuntime` | class | [10–202](../voice_runtime.py#L10-L202) |
| `VoiceRuntime.__init__` | function/method | [11–32](../voice_runtime.py#L11-L32) |
| `VoiceRuntime.state` | function/method | [34–37](../voice_runtime.py#L34-L37) |
| `VoiceRuntime.last_error` | function/method | [39–42](../voice_runtime.py#L39-L42) |
| `VoiceRuntime.is_busy` | function/method | [44–45](../voice_runtime.py#L44-L45) |
| `VoiceRuntime.submit` | function/method | [47–65](../voice_runtime.py#L47-L65) |
| `VoiceRuntime._request_stop_locked` | function/method | [67–77](../voice_runtime.py#L67-L77) |
| `VoiceRuntime.stop` | function/method | [79–86](../voice_runtime.py#L79-L86) |
| `VoiceRuntime.cancel_tag` | function/method | [88–102](../voice_runtime.py#L88-L102) |
| `VoiceRuntime._spawn_locked` | function/method | [104–118](../voice_runtime.py#L104-L118) |
| `VoiceRuntime._dispose_locked` | function/method | [120–130](../voice_runtime.py#L120-L130) |
| `VoiceRuntime._tick_locked` | function/method | [132–171](../voice_runtime.py#L132-L171) |
| `VoiceRuntime._supervise` | function/method | [173–187](../voice_runtime.py#L173-L187) |
| `VoiceRuntime.close` | function/method | [189–202](../voice_runtime.py#L189-L202) |

## parts_catalog.py

I collected component descriptions and synonyms to connect the operator's language to model codes and synthetic colours.

| Symbol | Kind | Lines |
|---|---|---|
| `build_catalog_text` | function/method | [245–259](../parts_catalog.py#L245-L259) |

## generate_silhouettes.py

I prepare metric silhouettes offline so the runtime only has to load, scale and rotate them.

| Symbol | Kind | Lines |
|---|---|---|
| `auto_flatten` | function/method | [17–38](../generate_silhouettes.py#L17-L38) |
| `mesh_outline_polygon` | function/method | [41–65](../generate_silhouettes.py#L41-L65) |
| `mesh_outline_polygon.fill_holes` | function/method | [59–64](../generate_silhouettes.py#L59-L64) |
| `rasterize_polygon` | function/method | [68–85](../generate_silhouettes.py#L68-L85) |
| `rasterize_polygon.to_px` | function/method | [77–79](../generate_silhouettes.py#L77-L79) |
| `mask_to_rgba` | function/method | [88–93](../generate_silhouettes.py#L88-L93) |
| `main` | function/method | [96–151](../generate_silhouettes.py#L96-L151) |

## orient_and_generate.py

I use manual 3D correction when automatic projection does not show the face needed for assembly.

| Symbol | Kind | Lines |
|---|---|---|
| `rot_matrix` | function/method | [21–36](../orient_and_generate.py#L21-L36) |
| `mesh_outline_polygon` | function/method | [39–64](../orient_and_generate.py#L39-L64) |
| `mesh_outline_polygon.fill_holes` | function/method | [58–63](../orient_and_generate.py#L58-L63) |
| `rasterize_polygon` | function/method | [67–84](../orient_and_generate.py#L67-L84) |
| `rasterize_polygon.to_px` | function/method | [76–78](../orient_and_generate.py#L76-L78) |
| `mask_to_rgba` | function/method | [87–92](../orient_and_generate.py#L87-L92) |
| `generate_one` | function/method | [95–106](../orient_and_generate.py#L95-L106) |
| `load_meta` | function/method | [109–114](../orient_and_generate.py#L109-L114) |
| `save_meta` | function/method | [117–119](../orient_and_generate.py#L117-L119) |
| `main` | function/method | [122–194](../orient_and_generate.py#L122-L194) |

## rotate_silhouette.py

I correct the in-plane direction of an otherwise valid PNG without repeating mesh projection.

| Symbol | Kind | Lines |
|---|---|---|
| `load_meta` | function/method | [11–16](../rotate_silhouette.py#L11-L16) |
| `save_meta` | function/method | [19–22](../rotate_silhouette.py#L19-L22) |
| `rotate_png` | function/method | [25–64](../rotate_silhouette.py#L25-L64) |
| `main` | function/method | [67–98](../rotate_silhouette.py#L67-L98) |

## create_class_map.py

I keep the correspondence between checkpoint indices, meshes and catalogue explicit before generating synthetic images.

| Symbol | Kind | Lines |
|---|---|---|
| `leggi_nomi` | function/method | [15–26](../create_class_map.py#L15-L26) |
| `abbina` | function/method | [29–38](../create_class_map.py#L29-L38) |
| `leggi_colori` | function/method | [52–72](../create_class_map.py#L52-L72) |
| `main` | function/method | [75–174](../create_class_map.py#L75-L174) |

## generate_meccano_dataset.py

I built synthetic scenes with geometry, materials and occlusions related to the bench, producing RGB images and COCO annotations.

| Symbol | Kind | Lines |
|---|---|---|
| `carica_pezzi` | function/method | [118–175](../generate_meccano_dataset.py#L118-L175) |
| `piazza_mano` | function/method | [291–326](../generate_meccano_dataset.py#L291-L326) |
| `randomizza_materiale` | function/method | [335–359](../generate_meccano_dataset.py#L335-L359) |
| `posa_camera` | function/method | [362–371](../generate_meccano_dataset.py#L362-L371) |
| `campiona` | function/method | [445–453](../generate_meccano_dataset.py#L445-L453) |
| `pulisci_coco` | function/method | [497–544](../generate_meccano_dataset.py#L497-L544) |

## prepare_training.py

I convert COCO annotations into YOLO format and augment only the training images.

| Symbol | Kind | Lines |
|---|---|---|
| `bbox_valide` | function/method | [61–78](../prepare_training.py#L61-L78) |
| `scrivi_yolo` | function/method | [108–117](../prepare_training.py#L108-L117) |
| `copia_originale` | function/method | [120–126](../prepare_training.py#L120-L126) |

## preview_colors.py

I compare colours under the renderer's lighting with a small preview instead of waiting for a full part simulation.

| Symbol | Kind | Lines |
|---|---|---|
