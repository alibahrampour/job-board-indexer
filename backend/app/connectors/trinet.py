from app.connectors.unavailable import UnavailablePlatformConnector


class TriNetConnector(UnavailablePlatformConnector):
    key = "trinet"
    platform_name = "TriNet"
    family = "E"
