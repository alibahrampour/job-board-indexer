from app.connectors.unavailable import UnavailablePlatformConnector


class JobboardlyConnector(UnavailablePlatformConnector):
    key = "jobboardly"
    platform_name = "Jobboardly"
    platform_type = "JOB_BOARD"
    family = "C"
