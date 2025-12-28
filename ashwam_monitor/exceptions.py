class AshwamMonitorError(Exception):
    """base error for all our stuff"""
    pass


class DataLoadError(AshwamMonitorError):
    """when we cant load a file"""
    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"failed to load {path}: {reason}")


class SchemaValidationError(AshwamMonitorError):
    """bad data in parser output"""
    def __init__(self, journal_id: str, field: str, issue: str):
        self.journal_id = journal_id
        super().__init__(f"{journal_id}: {field} - {issue}")


class ConfigError(AshwamMonitorError):
    """config is messed up"""
    pass


class InsufficientDataError(AshwamMonitorError):
    """not enough data to do anything meaningful"""
    def __init__(self, needed: int, got: int):
        super().__init__(f"need at least {needed} items but only got {got}")
