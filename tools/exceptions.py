import warnings

class SVUVWarning(UserWarning):
    """Base-class for non-fatal issues the SVUV parser reports."""

class SVUVError(Exception):
    """Base-class for *all* SVUV-parser exceptions."""

class MissingCitationWarning(SVUVWarning):
    """Data rows were encountered before a `!cite` directive."""

class SeparatorWarning(SVUVWarning):
    """Attempted to add a separator that already exists or remove a separator that doesn't exist."""

class ParseError(SVUVError):
    """Syntax or structural problem in a .svuv file."""

class CommandError(ParseError):
    """Syntax or structural problem in a command in a .svuv file."""

class UnknownUnitError(SVUVError):
    """A unit string was not found in the registry."""

class DimensionalityError(SVUVError):
    """The provided units are dimensionally incompatible."""