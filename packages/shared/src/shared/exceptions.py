class FileValidationError(Exception):
    """Raised when the file validation against its MD5 hash fails."""


class TemplateNotFoundError(Exception):
    """Raised when the template name is not found in HASH_VALUE."""
