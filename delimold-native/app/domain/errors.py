"""Business errors shared by the domain and application layers."""


class AppError(Exception):
    """Base class for expected application failures."""


class ValidationError(AppError):
    pass


class PermissionDenied(AppError):
    pass


class DataNotFound(AppError):
    pass


class AuthenticationFailed(AppError):
    pass


class StorageError(AppError):
    pass


class PublishError(AppError):
    pass


class ConfigurationError(AppError):
    pass
