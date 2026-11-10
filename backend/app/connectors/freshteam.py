from app.connectors.unavailable import UnavailablePlatformConnector


class FreshteamConnector(UnavailablePlatformConnector):
    key = "freshteam"
    platform_name = "Freshteam"
    family = "C"
