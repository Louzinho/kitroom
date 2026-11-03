class ApiError(Exception):
    """An expected failure, returned to the browser as JSON with an HTTP status."""

    def __init__(self, message, status=400, **extra):
        super().__init__(message)
        self.message = message
        self.status = status
        self.extra = extra
