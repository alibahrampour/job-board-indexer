from app.connectors.unavailable import UnavailablePlatformConnector


class PaycorConnector(UnavailablePlatformConnector):
    key = "paycor"
    platform_name = "Paycor"
    family = "D"
