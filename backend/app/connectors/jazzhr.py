from app.connectors.unavailable import UnavailablePlatformConnector


class JazzHRConnector(UnavailablePlatformConnector):
    key = "jazzhr"
    platform_name = "JazzHR"
    family = "C"
