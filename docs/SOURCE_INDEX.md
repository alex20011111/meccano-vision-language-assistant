# Source index

This index describes the English source edition published in the repository. The interactive report provides line-level browsing and links between UML elements and implementations.

## Runtime

### `meccano_tracker.py`
Coordinates RealSense acquisition, YOLO tracking, class stabilisation, depth processing, scene updates, the composition controller, the UI and voice commands. It is the application entry point.

Important elements: `ClassStabilizer`, `RawDetectionSnapshot`, `depth_at_bbox_center`, `box_plausible`, `deduplicate_detections`, `workspace_observations`, `draw_tracked_scene`, `start_voice`, `stop_voice`, `main`.

### `composition_controller.py`
Owns composition state and workspace prerequisites. It separates right-area occupancy from target placement and generates the operator-facing report of required, completed and remaining parts.

Important elements: `EmptyAreaGuard`, `ActionResult`, `CompositionController.observe`, `generate`, `finish`, `check_completion`, `report`, `verification_text`.

### `assembly_guide_cad.py`
Loads CAD silhouettes, scales them using work-surface depth, creates target slots, generates layouts and performs one-to-one matching between observed parts and targets.

Important elements: `SilhouetteLibrary`, `CadSlot`, `CadAssemblyGuide.generate_from_parts`, `_build_figure`, `_scaled_rotated_silhouette`, `_assign_parts`, `update`, `draw`.

### `composition_ui.py`
Renders the English OpenCV interface, buttons, part summary, right-area status, missing-part highlights and footer messages.

Important elements: `CompositionUI`, `draw_left_highlights`, `draw_workspace_blockers`, `workspace_status`.

### `part_orientation.py`
Estimates in-plane orientation from a part crop and applies temporal smoothing with the double-angle method.

Important elements: `estimate_angle_deg`, `AngleSmoother`.

### `voice_assistant.py`
Stores the queryable scene, parses spoken codes and descriptions, optionally calls the local LLM, constructs deterministic position responses and handles speech I/O inside the worker.

Important elements: `SceneState`, `describe_position`, `_words_to_number`, `VoiceAssistant`, `_voice_worker`.

### `voice_runtime.py`
Supervises the voice worker process and pipe, manages states, cancellation, priorities and late-result rejection without blocking video.

Important element: `VoiceRuntime`.

### `parts_catalog.py`
Contains the English semantic catalogue used by the UI and voice parser. Each entry provides a description, synonyms, colour and hole count when relevant.

Important element: `PARTS_CATALOG`, `build_catalog_text`.

## Offline CAD and dataset utilities

### `create_class_map.py`
Reads checkpoint class order, matches STL filenames and adds catalogue colours. Produces `class_map.json` without changing checkpoint indices.

### `generate_silhouettes.py`
Projects STL geometry into metric top-view RGBA silhouettes and writes `silhouettes_meta.json`.

### `orient_and_generate.py`
Interactive fallback for correcting a mesh's 3D orientation before silhouette generation.

### `rotate_silhouette.py`
Rotates an existing silhouette in the image plane and updates its metadata.

### `generate_meccano_dataset.py`
Builds synthetic BlenderProc scenes for the fixed top-down camera, including physical placement, material variation, lighting, backgrounds and optional hand occlusion. Writes COCO annotations.

### `prepare_training.py`
Filters COCO annotations, creates train/validation image sets, converts boxes to YOLO format, augments the training split and writes `data.yaml`.

### `preview_colors.py`
Renders a small material preview under HDRI lighting so plastic colours can be checked before full dataset generation.

## Test suite

The `tests/` directory contains regression and integration tests for composition logic, the right-area check, voice stop behaviour, main-loop integration and the English-language edition.

Run:

```bash
python -m pip install -r requirements_dev.txt
python -m unittest discover -s tests -v
```

The software tests are offline. They do not replace a test with the physical RealSense camera, model weights, silhouette assets, microphone and local language model.

## Documentation files

- `README.md` — repository overview and operating controls.
- `WEB_REPORT.md` — how to open the interactive report.
- `docs/TRAINING.md` — first 150-photo model and later synthetic-data fine-tuning.
- `docs/DECISIONS.md` — retained design choices and project scope.
- `docs/UML_AND_CODE.md` — logical and sequential code walkthrough.
- `docs/VERIFICATION.md` — test scope and limitations.
- `report/index.html` — full English report with figures, UML and source browser.
