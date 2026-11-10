from app.connectors.unavailable import UnavailablePlatformConnector


class BrassRingConnector(UnavailablePlatformConnector):
    key = "brassring"
    platform_name = "BrassRing"
    family = "D"
