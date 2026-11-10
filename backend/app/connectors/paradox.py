from app.connectors.unavailable import UnavailablePlatformConnector


class ParadoxConnector(UnavailablePlatformConnector):
    key = "paradox"
    platform_name = "Paradox"
    family = "D"
