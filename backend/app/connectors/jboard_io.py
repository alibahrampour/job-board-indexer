from app.connectors.unavailable import UnavailablePlatformConnector


class JBoardIOConnector(UnavailablePlatformConnector):
    key = "jboard_io"
    platform_name = "JBoard.io"
    platform_type = "JOB_BOARD"
    family = "C"
