from app.connectors.unavailable import UnavailablePlatformConnector


class ComeetConnector(UnavailablePlatformConnector):
    key = "comeet"
    platform_name = "Comeet"
    family = "B"
