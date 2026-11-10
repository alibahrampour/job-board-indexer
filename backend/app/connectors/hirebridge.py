from app.connectors.unavailable import UnavailablePlatformConnector


class HireBridgeConnector(UnavailablePlatformConnector):
    key = "hirebridge"
    platform_name = "HireBridge"
    family = "E"
