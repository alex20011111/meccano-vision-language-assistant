# Meccano Vision–Language Assistant

## RGB-D perception, stable tracking and voice-assisted assembly

During my internship, I developed a visual and voice assistant for a Meccano workbench. I started with YOLO part recognition and focused on keeping the information consistent: following a component as it moves, stabilising its class and using its position to guide the operator.

The system combines a RealSense RGB-D camera, YOLO, ByteTrack, a class stabiliser, CAD-derived silhouettes and a local language model. It is an operator-assistance prototype, not an autonomous robot controller. It does not include ROS/ROS2 nodes or a VLM that receives images directly.

**[Project report: HTML source](report/index.html)** · **[How to view the report](WEB_REPORT.md)** · **[UML and code](docs/UML_AND_CODE.md)** · **[Source index](docs/SOURCE_INDEX.md)**

## From the first model to fine-tuning

**I trained the first `best.pt` on 150 photographs that I labelled manually in Roboflow.** This was the initial part-recognition dataset, before synthetic generation from CAD. Roboflow was the annotation tool.

I used that model to integrate tracking and class stabilisation. I then generated synthetic scenes from the CAD models, prepared YOLO annotations and continued training from the existing weights. The **first training run on 150 photographs** and the **later synthetic-data fine-tuning** are separate stages. The report's training plots describe the later stage, not the initial model's performance.

[Model development and data preparation](docs/TRAINING.md)

## How it works

```text
RGB-D camera → YOLO → ByteTrack → class stabilisation
                                      ↓
                                  scene state
                                  ↙        ↘
                        silhouette guide   voice assistant
                        and placements     text → code → position
```

I separated perception from language interpretation. The language model uses the catalogue to resolve a part description; Python selects the observed instances and constructs the position response. Voice processing runs in a local process separate from the video loop.

## The workbench and kit

The complete HTML report includes the RealSense camera photograph, the Meccano kit overview, translated workbench screenshots and the training figures. The RGB image feeds the detector, while depth and camera intrinsics support position estimates and silhouette scaling. The kit overview provides context for the component catalogue; the screwdriver labelled A090 belongs to the tools, not to the assembly-part inventory.

## Source and startup

The repository contains **15 application/preparation modules and seven test files**. Explanations are kept in the documentation rather than decorative source comments.

[Files, classes and functions](docs/SOURCE_INDEX.md) · [Main application](meccano_tracker.py) · [Offline tests](tests/)

From the repository root, with weights, silhouettes and the tracker configuration available locally:

```bash
python -m pip install -r requirements.txt
python meccano_tracker.py --model "path/to/best.pt" --silhouettes "path/to/silhouettes" --tracker "path/to/meccano_bytetrack.yaml" --no-voice
```

For voice interaction, install `requirements_voice.txt`, prepare the configured local model and omit `--no-voice`. This edition uses English speech recognition, an English catalogue and English TTS voice selection. CAD, rendering and dataset tools use separate dependencies; they are not required for simply viewing the report.

## Workbench controls

| Control | Action |
|---|---|
| **G / Space** | Start a composition from the stably recognised left-hand parts once the right-hand area is clear. Does not replace an active composition. |
| **N** | Request a different layout when the right-area check permits it. |
| **V / I** | Show or hide the summary and left-side cues for parts still needed. |
| **R** | Ask for a part by code or description. |
| **S** | Stop the current voice task without stopping the camera or tracking. |
| **X** | Clear the composition, retain tracking and check whether parts need returning. |
| **Q / Esc** | Close the application and release its resources. |

I kept the **right-hand occupancy check enabled**. It is separate from the continuous placement check against each target. Parts remaining in the construction region after X or completion trigger the written and spoken warning **RETURN THE PARTS TO THE STARTING AREA**.

Experimental data collection is not part of this runtime.

## Documentation

The [HTML report](report/index.html) contains the project narrative, camera and kit illustrations, bench screenshots, training plots and the interactive UML/code guide. The guide follows data from offline preparation through the frame loop and voice response to shutdown. Module contracts explain responsibilities, inputs, outputs and dependencies. The source reader uses the line numbers of the English source edition.

[UML and execution path](docs/UML_AND_CODE.md) · [Source index](docs/SOURCE_INDEX.md) · [Design decisions](docs/DECISIONS.md) · [Viewing the HTML](WEB_REPORT.md)

## Classes and results

**A090 and A823 were erroneous labels in the assembly dataset; neither is a component class in the working inventory.** A132 is the working pin code. A622 and A632 are distinct parts. Hand is an auxiliary class, not a composition component. Physical part identity and checkpoint index order remain separate: removing names from a list without migrating annotations would change subsequent class meanings.

The plots cover 50 epochs of the later training stage and synthetic validation. They describe detector convergence, not tracking continuity, voice quality or operator benefit. The per-class AP chart has inconsistencies with the taxonomy and confusion matrices. Its name-to-value alignment needs checking before using it to rank parts.

## Reproduction and compatibility

Weights, the original photographs, synthetic dataset, STL models, silhouette assets and the bench configuration are separate resources. Illustrations do not replace those assets. The training plots and interface illustrations are presented with English labels while preserving the underlying numerical data. The report distinguishes documentation graphics from new experimental measurements.

Core runtime module names, public runtime interfaces and part codes remain stable. Offline preparation utilities use English filenames and command-line labels in this edition. User-facing text, documentation and workflow names are English. Git history has not been rewritten.

Run the offline test suite with:

```bash
python -m pip install -r requirements_dev.txt
python -m unittest discover -s tests -v
```

[Verification scope and results](docs/VERIFICATION.md)
