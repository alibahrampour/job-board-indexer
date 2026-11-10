from app.connectors.unavailable import UnavailablePlatformConnector


class SmartJobBoardConnector(UnavailablePlatformConnector):
    key = "smartjobboard"
    platform_name = "SmartJobBoard"
    platform_type = "JOB_BOARD"
    family = "C"
