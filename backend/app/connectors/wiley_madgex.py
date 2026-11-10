from app.connectors.unavailable import UnavailablePlatformConnector


class WileyMadgexConnector(UnavailablePlatformConnector):
    key = "wiley_madgex"
    platform_name = "Wiley Madgex"
    platform_type = "JOB_BOARD"
    family = "C"
