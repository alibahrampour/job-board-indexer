from app.connectors.unavailable import UnavailablePlatformConnector


class TaleoConnector(UnavailablePlatformConnector):
    key = "taleo"
    platform_name = "Taleo"
    family = "C"
