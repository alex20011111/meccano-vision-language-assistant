# Verification

## Python

The English edition passes **133 unittest tests**, including the 124 existing regression tests and nine language-specific tests. The suite covers composition counts, one-to-one matching, right-area checks, voice cancellation, late-result rejection and simulated main-loop behaviour. Language tests cover English transcription settings, numeric code parsing, position messages, the return warning, catalogue text, ordinals and TTS selection.

All published Python files compile. ClassStabilizer was compared against the preceding version using its syntax tree: the only changed constants were the two translated inheritance-log fragments. Its tracking logic and numerical parameters were unchanged. The source-snapshot test was updated to the English source hash, without removing assertions.

## Documentation

The report has 15 indexed modules and 217 symbols. Symbol links and line ranges refer to the English source files. Embedded images, chapter navigation, source search, diagram links and mobile layout are checked separately from the runtime.

## Scope

These are offline software and document checks. They are not a new test with a RealSense camera, the trained weights, CAD silhouette assets, microphone or installed speech engine. Synthetic detector plots do not establish real-workbench performance or operator benefit.

Run the suite from the repository root:

```bash
python -m pip install -r requirements_dev.txt
python -m unittest discover -s tests -v
```
