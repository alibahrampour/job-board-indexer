from app.connectors.unavailable import UnavailablePlatformConnector


class PaycomConnector(UnavailablePlatformConnector):
    key = "paycom"
    platform_name = "Paycom"
    family = "D"
