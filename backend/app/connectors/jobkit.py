from app.connectors.unavailable import UnavailablePlatformConnector


class JobKitConnector(UnavailablePlatformConnector):
    key = "jobkit"
    platform_name = "JobKit"
    platform_type = "JOB_BOARD"
    family = "C"
