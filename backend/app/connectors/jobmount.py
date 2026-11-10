from app.connectors.unavailable import UnavailablePlatformConnector


class JobMountConnector(UnavailablePlatformConnector):
    key = "jobmount"
    platform_name = "JobMount"
    platform_type = "JOB_BOARD"
    family = "C"
