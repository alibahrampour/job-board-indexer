from app.connectors.unavailable import UnavailablePlatformConnector


class ICIMSConnector(UnavailablePlatformConnector):
    key = "icims"
    platform_name = "iCIMS"
    family = "C"
