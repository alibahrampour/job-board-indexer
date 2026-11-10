from app.connectors.unavailable import UnavailablePlatformConnector


class JobiqoConnector(UnavailablePlatformConnector):
    key = "jobiqo"
    platform_name = "Jobiqo"
    platform_type = "JOB_BOARD"
    family = "C"
