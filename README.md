# Parsers

A dual repository (JavaScript and Python) containing parsers.

## Measurements

`MeasurementSetParser` writes the folder `mat3ra-upload` takes (`set.json`, `<measurement>/measurement.json`, `<measurement>/files/`) from an instrument's output and the workflow document of its measurements. `format` names the application:

- `applications.asylum_spm.loop`: an Asylum Research run folder (`summary.json`, `loops/<point>/*.npy`)
- `applications.xrf_instrument.map`: an XRF grid table, one row per site
- `applications.dc_iv_instrument.sweep`: a folder with `IV_Volts.txt` and `IV_Amps.txt`

```python
from mat3ra.parsers.entities.measurement_set import MeasurementSetParser

MeasurementSetParser(run_folder, workflow, format="applications.asylum_spm.loop").write(upload_folder)
```
