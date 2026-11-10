from app.connectors.unavailable import UnavailablePlatformConnector


class FirstStageConnector(UnavailablePlatformConnector):
    key = "firststage"
    platform_name = "FirstStage"
    family = "E"
