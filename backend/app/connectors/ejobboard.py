from app.connectors.unavailable import UnavailablePlatformConnector


class EJobBoardConnector(UnavailablePlatformConnector):
    key = "ejobboard"
    platform_name = "eJobBoard"
    platform_type = "JOB_BOARD"
    family = "C"
