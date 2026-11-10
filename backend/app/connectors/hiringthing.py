from app.connectors.unavailable import UnavailablePlatformConnector


class HiringThingConnector(UnavailablePlatformConnector):
    key = "hiringthing"
    platform_name = "HiringThing"
    family = "C"
