import json
from collections import defaultdict
from pathlib import Path, PureWindowsPath

import numpy
from mat3ra.parsers import BaseParser


def parameter_statistics(parameters_per_loop, key):
    """Mean, population standard deviation and count of one parameter over the loops that carry it."""
    values = [loop_parameters[key] for loop_parameters in parameters_per_loop if loop_parameters[key] is not None]
    return {"value": float(numpy.mean(values)), "standardDeviation": float(numpy.std(values)), "count": len(values)}


class AsylumSpmParser(BaseParser):
    """
    Asylum Research run folder parser: summary.json and loops/<point>/*.npy, one measurement per pad.

    Args:
        content (str or Path): run folder path.
        workflow (dict): workflow document of the measurements.
        version (str): instrument version.
    """

    def __init__(self, content, workflow, version: str = "1.0"):
        super().__init__(content, version=version)
        self.workflow = workflow

    def point_folder(self, entry):
        """The folder of an entry's loop files, loops/<point>, named after the folder of its bias_on_path."""
        return Path(self.content) / "loops" / PureWindowsPath(entry["segmentation"]["bias_on_path"]).parent.name

    def hysteresis_loop(self, entries):
        """The pad's hysteresis_loop property, None unless both conditions share a bias axis; loops per condition."""
        biases, responses, parameters = [], {"on": [], "off": []}, {}
        for condition in responses:
            parameters_per_loop = [entry["loop_params"][f"{condition}_field"] for entry in entries]
            for entry, loop_parameters in zip(entries, parameters_per_loop):
                paths = [self.point_folder(entry) / f"{channel}_{condition}.npy" for channel in ("bias", "X", "Y")]
                if not all(path.exists() for path in paths):
                    continue
                bias, x, y = (numpy.load(path).astype(float) for path in paths)
                angle = numpy.radians(loop_parameters["phase_offset_deg"])
                biases.append(bias)
                # X and Y are the lock-in quadratures; turned by the loop's phase offset,
                # the switching lies along one axis
                responses[condition].append(x * numpy.cos(angle) + y * numpy.sin(angle))
            parameters[condition] = {
                "imprint": parameter_statistics(parameters_per_loop, "imprint_v"),
                "coerciveVoltage": {
                    "rising": parameter_statistics(parameters_per_loop, "v_c_rising"),
                    "falling": parameter_statistics(parameters_per_loop, "v_c_falling"),
                },
                "loopWidth": parameter_statistics(parameters_per_loop, "loop_width_v"),
                "loopHeight": parameter_statistics(parameters_per_loop, "loop_height_m"),
                "remanentResponse": {
                    "rising": parameter_statistics(parameters_per_loop, "remnant_rising_m"),
                    "falling": parameter_statistics(parameters_per_loop, "remnant_falling_m"),
                },
            }
        loop_counts = {condition: len(responses[condition]) for condition in responses}
        if (
            not responses["on"]
            or not responses["off"]
            or any(not numpy.array_equal(bias, biases[0]) for bias in biases)
        ):
            return None, loop_counts
        return {
            "name": "hysteresis_loop",
            "legend": ["on", "off"],
            "xAxis": {"label": "bias", "units": "V"},
            "yAxis": {"label": "response", "units": "m"},
            "xDataArray": biases[0].tolist(),
            "yDataSeries": [numpy.mean(responses[condition], axis=0).tolist() for condition in ("on", "off")],
            "parameters": parameters,
        }, loop_counts

    def measurement(self, summary, label, entries):
        """The measurement document of the pad at site `label`, built from its summary entries."""
        property_document, loop_counts = self.hysteresis_loop(entries)
        technique = " ".join(word if word.isupper() else word.lower() for word in self.workflow["name"].split())
        kind = summary["recipe"]["per_site"][entries[0]["labels"]["step_index"]]["kind"]
        loop_count = sum(loop_counts.values())
        loops_per_condition = ", ".join(f"{count} {condition}-field" for condition, count in loop_counts.items())
        loops = f"{loop_count} {kind}s ({loops_per_condition})" if loop_count else f"no {kind}s"
        return {
            "name": f"{summary['run']['name']} {label}",
            "description": f"{technique} at site {label}, {loops}",
            "status": "finished",
            "setup": {
                "instrument": {"name": "Asylum Research"},
                "session": summary["run"],
                "settings": {
                    group: settings
                    for group, settings in entries[0]["achieved"].items()
                    if group not in ("stage_position", "probe_position")
                },
            },
            "workflow": self.workflow,
            "sample": {"name": label, "metadata": {"position": entries[0]["achieved"]["stage_position"]}},
            **({"properties": [property_document]} if property_document else {}),
            "metadata": {
                "measurements": [
                    {
                        **entry,
                        "achieved": {key: value for key, value in entry["achieved"].items() if key != "stage_position"},
                    }
                    for entry in entries
                ]
            },
        }

    def parse(self):
        """Returns {"content": {"set", "measurements", "files"}, "version"}."""
        run_folder = Path(self.content)
        summary = json.loads((run_folder / "summary.json").read_text())
        entries_by_pad = defaultdict(list)
        for entry in summary["measurements"]:
            entries_by_pad[entry["labels"]["site_label"]].append(entry)
        measurements = {label: self.measurement(summary, label, entries) for label, entries in entries_by_pad.items()}
        files = {
            label: {
                path.relative_to(run_folder).as_posix(): str(path)
                for entry in entries
                for path in self.point_folder(entry).glob("*")
            }
            for label, entries in entries_by_pad.items()
        }
        set_document = {
            "name": summary["run"]["name"],
            "description": "",
            "metadata": {key: value for key, value in summary.items() if key != "measurements"},
        }
        return {"content": {"set": set_document, "measurements": measurements, "files": files}, "version": self.version}
