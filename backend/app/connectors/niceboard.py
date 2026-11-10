from app.connectors.unavailable import UnavailablePlatformConnector


class NiceboardConnector(UnavailablePlatformConnector):
    key = "niceboard"
    platform_name = "Niceboard"
    platform_type = "JOB_BOARD"
    family = "C"
