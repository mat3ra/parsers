# Parsers

A dual repository (JavaScript and Python) containing parsers.

## 1. Measurements

`mat3ra-parse` writes the folder `mat3ra-upload` takes (`set.json`, `<measurement>/measurement.json`, `<measurement>/files/`) from an instrument's output, with the instrument's example workflow from mat3ra-fixtures. Instruments:

- `asylum-spm`: an Asylum Research run folder (`summary.json`, `loops/<point>/*.npy`)
- `xrf-instrument`: an XRF grid table, one row per site
- `dc-iv-instrument`: a folder with `IV_Volts.txt` and `IV_Amps.txt`

The install needs Python 3.10+, git and git-lfs (`git lfs install` once); without git-lfs the example data and workflows arrive as pointer files.

```bash
pip install "mat3ra-parsers[alphafilm] @ git+https://github.com/mat3ra/parsers.git@alphafilm"
mat3ra-parse asylum-spm <run folder> <output folder>
```

From Python: `MeasurementSetParser(run_folder, workflow, format="instruments.asylum_spm").write(output_folder)`, imported from `mat3ra.parsers.entities.measurement_set`.
