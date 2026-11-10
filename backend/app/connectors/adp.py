from app.connectors.unavailable import UnavailablePlatformConnector


class ADPConnector(UnavailablePlatformConnector):
    key = "adp"
    platform_name = "ADP"
    family = "D"
