from mat3ra.utils import factory as factory


class ParserFactory(factory.BaseFactory):
    """
    Parser Factory class.
    """

    __class_registry__ = {
        "applications.espresso.pw_x.stdin": (
            "mat3ra.parsers.applications.espresso.pw_x.stdin.parser.EspressoPwxStdinParser"
        ),
        "applications.vasp.stdin": "mat3ra.parsers.applications.vasp.VASPStdinParser",
        "applications.asylum_spm.loop": "mat3ra.parsers.applications.asylum_spm.loop.parser.AsylumSpmLoopParser",
        "applications.xrf_instrument.map": (
            "mat3ra.parsers.applications.xrf_instrument.map.parser.XrfInstrumentMapParser"
        ),
        "applications.dc_iv_instrument.sweep": (
            "mat3ra.parsers.applications.dc_iv_instrument.sweep.parser.DcIvInstrumentSweepParser"
        ),
    }
