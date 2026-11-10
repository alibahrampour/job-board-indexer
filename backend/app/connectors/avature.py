from app.connectors.unavailable import UnavailablePlatformConnector


class AvatureConnector(UnavailablePlatformConnector):
    key = "avature"
    platform_name = "Avature"
    family = "C"
