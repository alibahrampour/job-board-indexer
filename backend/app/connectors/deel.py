from app.connectors.unavailable import UnavailablePlatformConnector


class DeelConnector(UnavailablePlatformConnector):
    key = "deel"
    platform_name = "Deel"
    family = "E"
