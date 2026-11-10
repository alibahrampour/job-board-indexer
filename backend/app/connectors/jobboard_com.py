from app.connectors.unavailable import UnavailablePlatformConnector


class JobBoardComConnector(UnavailablePlatformConnector):
    key = "jobboard_com"
    platform_name = "JobBoard.com"
    platform_type = "JOB_BOARD"
    family = "C"
