class PocError(Exception):
    """An actionable error suitable for display by the CLI and testing UI."""


class DatabaseError(PocError):
    pass


class ExternalServiceError(PocError):
    pass
