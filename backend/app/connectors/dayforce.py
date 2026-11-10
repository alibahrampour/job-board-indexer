from app.connectors.unavailable import UnavailablePlatformConnector


class DayforceConnector(UnavailablePlatformConnector):
    key = "dayforce"
    platform_name = "Dayforce"
    family = "D"
