from app.connectors.unavailable import UnavailablePlatformConnector


class HireHiveConnector(UnavailablePlatformConnector):
    key = "hirehive"
    platform_name = "HireHive"
    family = "E"
