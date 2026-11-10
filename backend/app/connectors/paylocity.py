from app.connectors.unavailable import UnavailablePlatformConnector


class PaylocityConnector(UnavailablePlatformConnector):
    key = "paylocity"
    platform_name = "Paylocity"
    family = "B"
