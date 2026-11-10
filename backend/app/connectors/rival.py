from app.connectors.unavailable import UnavailablePlatformConnector


class RivalConnector(UnavailablePlatformConnector):
    key = "rival"
    platform_name = "Rival"
    family = "E"
