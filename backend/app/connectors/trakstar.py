from app.connectors.unavailable import UnavailablePlatformConnector


class TrakstarConnector(UnavailablePlatformConnector):
    key = "trakstar"
    platform_name = "Trakstar"
    family = "C"
