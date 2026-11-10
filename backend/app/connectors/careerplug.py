from app.connectors.unavailable import UnavailablePlatformConnector


class CareerPlugConnector(UnavailablePlatformConnector):
    key = "careerplug"
    platform_name = "CareerPlug"
    family = "C"
