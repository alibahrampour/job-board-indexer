from app.connectors.unavailable import UnavailablePlatformConnector


class CSODConnector(UnavailablePlatformConnector):
    key = "csod"
    platform_name = "CSOD"
    family = "D"
