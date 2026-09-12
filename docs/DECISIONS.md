# Design decisions

These are the choices retained in the prototype, separate from possible extensions.

## D01 — Construction-area occupancy

I kept the right-area occupancy check. Start and layout changes respect it; G does not replace an active composition.

Occupancy is separate from checking an individual part against a silhouette. A part outside all targets can block generation without completing a slot. Observations used for occupancy follow plausibility filtering and visible diagnostics.

## D02 — Continuous tracking and voice stop

Tracking boxes remain visible throughout the task. Stop voice cancels the local voice process without closing the camera or resetting IDs. X finishes and clears the composition, not tracking.

When parts remain in the construction region after X or completion, the written and spoken warning is **RETURN THE PARTS TO THE STARTING AREA**. Stopping speech does not clear the visual workspace warning.

## D03 — Physical codes and model indices

A090 and A823 were introduced as incorrect assembly labels. They do not require component STL files or silhouettes. A090 in the kit illustration identifies a tool, which is outside the assembly inventory. A132 is the working pin code; A622 and A632 are distinct. Hand is an auxiliary class excluded from the composition.

I keep this physical taxonomy separate from checkpoint index order. Removing intermediate names requires a coherent migration of labels and configuration. The code guide identifies constraints that the current implementation does not yet enforce explicitly.

## D04 — Prototype scope

I integrated RGB-D perception, YOLO, ByteTrack, temporal stabilisation, CAD geometry and voice interaction with a local LLM. The language model interprets requests; it does not calculate coordinates or command actuators.

The prototype does not include a robot arm, ROS/ROS2 nodes or an image-input VLM. Those belong to the broader training context and possible future work.

## D05 — Evaluation

Bench screenshots and training plots are different forms of evidence. The screenshot containing TRIAL and a timer shows an earlier interface; experimental collection is absent from the current runtime.

Detector curves do not measure ID continuity, voice accuracy or operator benefit. The per-class AP chart also needs checking against the numeric outputs because it conflicts with the taxonomy and confusion matrices. I do not use it as a verified ranking of component performance.

## D06 — Origin of the first best.pt

The first model was trained on **150 photographs manually labelled in Roboflow**. I used it for initial RGB-D recognition and tracking, then continued training on synthetic data prepared from CAD.

Manual photo annotation and automatic render annotation are separate stages. Later split sizes, epochs and metrics are not attributed to the first run. [Training path](TRAINING.md).

## D07 — English edition

The report, UML explanations, interface labels, console messages, catalogue descriptions and prompts use English. Speech recognition, spoken-code parsing and TTS selection are configured for English. Geometric thresholds, tracking behaviour and part codes remain unchanged.

Existing module names, public symbols and asset/configuration keys remain available for compatibility. Training plots and interface illustrations are presented with English labels while preserving their underlying data. The report distinguishes documentation graphics from new experimental measurements. Commit history is preserved.

[Repository overview](../README.md) · [UML and code](UML_AND_CODE.md)
