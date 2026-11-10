from app.connectors.unavailable import UnavailablePlatformConnector


class PageUpConnector(UnavailablePlatformConnector):
    key = "pageup"
    platform_name = "PageUp"
    family = "C"
