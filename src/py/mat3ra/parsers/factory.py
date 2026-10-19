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
        "instruments.asylum_spm": "mat3ra.parsers.instruments.asylum_spm.parser.AsylumSpmParser",
        "instruments.xrf_instrument": "mat3ra.parsers.instruments.xrf_instrument.parser.XrfInstrumentParser",
        "instruments.dc_iv_instrument": "mat3ra.parsers.instruments.dc_iv_instrument.parser.DcIvInstrumentParser",
    }
