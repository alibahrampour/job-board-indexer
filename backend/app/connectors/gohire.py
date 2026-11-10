from app.connectors.unavailable import UnavailablePlatformConnector


class GoHireConnector(UnavailablePlatformConnector):
    key = "gohire"
    platform_name = "GoHire"
    family = "C"
