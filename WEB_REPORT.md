# Viewing the project report

The full report is in **[report/index.html](report/index.html)**. It includes the project narrative, camera and kit images, bench screenshots, training plots, nine linked UML diagrams and the complete code reader.

## Open it locally

Download the repository ZIP, extract it and open **`report/index.html`** with Chrome, Edge or Firefox. Alternatively, open the standalone **`Meccano_Report.html`** file. Images, diagrams, code and scripts are embedded; no Python, camera, microphone, GPU or model is needed to read it.

GitHub's file page normally shows HTML source rather than rendering it as a website. GitHub Pages is a separate publication mechanism. Its workflow status determines whether the public site has actually been deployed.

## Reading path

**Context → initial dataset → pipeline → modules → UML and code → results → reproduction → limitations.**

The initial `best.pt` was trained on **150 photographs manually labelled in Roboflow**. Synthetic BlenderProc generation and later fine-tuning are discussed separately. Later plots do not establish the initial model's performance.

The interactive code section offers five views: a twelve-stage execution path, linked UML, files/functions, numbered source and a checksum index. Select a class or sequence message to open its implementation, then inspect statements and their branches.

## Illustrations and results

The report includes the camera photograph, the kit overview, workspace screenshots and eleven detector plots. The camera photograph shows the device, not its mounting arrangement. The TRIAL screenshot shows an earlier interface.

English captions explain the original figures. Losses, precision/recall, mAP, F1 and confusion matrices are interpreted separately. The per-class AP alignment issue remains identified; missing numerical results are not reconstructed from plotted pixels.

## Working configuration

The right-area check stays enabled. G starts only after the prerequisites are met and never replaces an active layout. N requests a change when the area is clear. Tracking and placement checking continue throughout. Stop voice cancels audio without resetting IDs.

A090/A823 are erroneous assembly labels; tools are outside the composition. A132 is the working pin code, A622/A632 are distinct, and Hand is auxiliary.

## Reproduction

The code reader contains the English source edition with current symbol ranges. Model weights, datasets, CAD assets and bench settings remain separate. Software tests, real-hardware checks and experimental evaluation of the interaction are distinct activities.

[Repository overview](README.md) · [Training](docs/TRAINING.md) · [Design decisions](docs/DECISIONS.md) · [UML and code](docs/UML_AND_CODE.md)
