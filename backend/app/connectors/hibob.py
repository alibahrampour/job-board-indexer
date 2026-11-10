from app.connectors.unavailable import UnavailablePlatformConnector


class HiBobConnector(UnavailablePlatformConnector):
    key = "hibob"
    platform_name = "HiBob"
    family = "D"
