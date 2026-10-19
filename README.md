# Parsers

A dual repository (JavaScript and Python) containing parsers.

## 1. Measurements

`mat3ra-parse` writes the folder `mat3ra-upload` takes (`set.json`, `<measurement>/measurement.json`, `<measurement>/files/`) from an instrument's output, with the example workflow of its application from mat3ra-fixtures. Applications:

- `asylum-spm`: an Asylum Research run folder (`summary.json`, `loops/<point>/*.npy`)
- `xrf-instrument`: an XRF grid table, one row per site
- `dc-iv-instrument`: a folder with `IV_Volts.txt` and `IV_Amps.txt`

```bash
mat3ra-parse asylum-spm <run folder> <output folder>
```

From Python: `MeasurementSetParser(run_folder, workflow, format="applications.asylum_spm.loop").write(output_folder)`, imported from `mat3ra.parsers.entities.measurement_set`.
