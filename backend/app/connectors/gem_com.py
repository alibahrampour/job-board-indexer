from app.connectors.unavailable import UnavailablePlatformConnector


class GemComConnector(UnavailablePlatformConnector):
    key = "gem_com"
    platform_name = "Gem.com"
    family = "B"
