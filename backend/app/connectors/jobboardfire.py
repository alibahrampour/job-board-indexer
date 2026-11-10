from app.connectors.unavailable import UnavailablePlatformConnector


class JobBoardFireConnector(UnavailablePlatformConnector):
    key = "jobboardfire"
    platform_name = "JobBoardFire"
    platform_type = "JOB_BOARD"
    family = "C"
