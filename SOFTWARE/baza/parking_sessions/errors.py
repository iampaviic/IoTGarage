class SessionError(Exception):
    """Base class for session problems the caller is expected to handle."""


class ActiveSessionExists(SessionError):
    """The plate already has an ACTIVE session (vehicle is already inside)."""

    def __init__(self, plate: str, session_id: str):
        self.plate = plate
        self.session_id = session_id
        super().__init__("plate %s already has active session %s" % (plate, session_id))


class SessionNotFound(SessionError):
    pass


class SessionNotActive(SessionError):
    pass
