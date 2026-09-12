# Training: from labelled photographs to synthetic data

## 1. The first model

I obtained the first `best.pt` by training on **150 photographs manually labelled in Roboflow**. Initial Meccano recognition therefore started with a hand-labelled photographic dataset, not images generated from CAD.

The number 150 refers to the initial dataset, not images per class or training epochs. Its split manifest is not included, so I do not give a numerical train/validation/test breakdown for that stage. The hyperparameters and metrics of the later fine-tuning run do not describe the first run.

Roboflow was my annotation tool. This does not establish that training took place on Roboflow's cloud service.

## 2. From detection to tracking

I used the first model as the starting point for the RGB-D application. Its main issue was class instability: a part could receive different labels in successive frames, so individual detections were insufficient for continuous assistance.

I integrated ByteTrack for temporal association, an observation history for class voting and a lock to retain the selected class. Ghost recovery handles some temporary track losses. These changes affect the pipeline; they are neither another training run nor a measured increase in mAP.

## 3. The second path: synthetic data from CAD

I then reused the CAD models to increase scene variety. With BlenderProc, I varied part positions, rotations, materials, lighting, backgrounds and hand occlusions. Annotations come from the simulated scene rather than manual labelling of each render.

```text
150 photos → manual Roboflow labels → initial training → first best.pt
                                                               │
CAD / STL → BlenderProc → COCO annotations → YOLO preparation ────┤
                                                               ↓
                                                        later fine-tuning
```

The two paths have different origins: photographs form the initial dataset; renders and their transformed copies belong to the later preparation stage.

## 4. Conversion and augmentation

`create_class_map.py` reads checkpoint class order and links codes to STL files and catalogue colours. `generate_meccano_dataset.py` creates scenes and annotations. `prepare_training.py` produces images, YOLO labels and `data.yaml`.

The preparer splits originals before transformations and augments training images only. The preparation output reports **898 original and 980 augmented training images, plus 122 validation images**: 2,000 in total. This is not the split of the original 150 photographs and does not mean 2,000 original photographs.

The preparer's split is image-level. Independence also depends on views belonging to the same scene and on data already used to train the initial checkpoint.

## 5. Fine-tuning and interpretation

I continued training from the existing `best.pt` using the prepared synthetic dataset. This fine-tuning is separate from the first manually labelled photographic run.

The available plots show 50 epochs. A separate training command specifies 60; the complete run log and `args.yaml` are needed to explain the difference. I do not attribute it to a particular stopping condition without those records.

Synthetic validation measures convergence and performance within the rendering domain. It is not, on its own, a real-bench test. A quantitative before/after comparison requires the same independent evaluation set and conditions. An image used to train the first model does not become independent simply because the model has subsequently been fine-tuned.

## 6. Labelling errors and index continuity

**A090 and A823 are erroneous assembly-part labels.** The A090 tool shown in the kit illustration is outside the component inventory. A132 is the working pin code; A622 and A632 remain distinct; Hand is auxiliary.

Deleting two names from the middle of a checkpoint list would shift later indices. Annotation migration must be explicit and checked, without automatically assigning A090 or A823 to another component.

Bars attributed to these labels in the AP chart cannot be interpreted as performance on assembly parts. The chart is retained with the inconsistency identified. Correct evaluation requires the original numeric output and export mapping, not simply deleting bars from the image.

## 7. Files associated with a model

I keep the checkpoint, annotation version, split membership, code map, configuration and results together. Relevant files include `best.pt`, `data.yaml`, `args.yaml` and `results.csv`. Missing values are not inferred from another run.

[UML and code](UML_AND_CODE.md) · [Design decisions](DECISIONS.md) · [Repository overview](../README.md)
