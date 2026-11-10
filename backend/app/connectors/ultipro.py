from app.connectors.unavailable import UnavailablePlatformConnector


class UltiProConnector(UnavailablePlatformConnector):
    key = "ultipro"
    platform_name = "UltiPro"
    family = "B"
