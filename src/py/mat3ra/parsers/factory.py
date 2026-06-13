from mat3ra.utils import factory as factory


class ParserFactory(factory.BaseFactory):
    """
    Parser Factory class.
    """

    __class_registry__ = {
        "applications.espresso.pwin": "mat3ra.parsers.applications.espresso.pwin.EspressoPwinParser",
        "applications.vasp.stdin": "mat3ra.parsers.applications.vasp.VASPStdinParser",
    }
