from app.connectors.unavailable import UnavailablePlatformConnector


class DoverConnector(UnavailablePlatformConnector):
    key = "dover"
    platform_name = "Dover"
    family = "E"
