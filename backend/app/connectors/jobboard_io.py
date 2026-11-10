from app.connectors.unavailable import UnavailablePlatformConnector


class JobBoardIOConnector(UnavailablePlatformConnector):
    key = "jobboard_io"
    platform_name = "JobBoard.io"
    platform_type = "JOB_BOARD"
    family = "C"
