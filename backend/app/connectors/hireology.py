from app.connectors.unavailable import UnavailablePlatformConnector


class HireologyConnector(UnavailablePlatformConnector):
    key = "hireology"
    platform_name = "Hireology"
    family = "C"
