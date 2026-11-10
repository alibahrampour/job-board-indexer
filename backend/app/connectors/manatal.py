from app.connectors.unavailable import UnavailablePlatformConnector


class ManatalConnector(UnavailablePlatformConnector):
    key = "manatal"
    platform_name = "Manatal"
    family = "E"
