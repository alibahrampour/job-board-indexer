from app.connectors.unavailable import UnavailablePlatformConnector


class JobBoardHQConnector(UnavailablePlatformConnector):
    key = "jobboardhq"
    platform_name = "jobBoardHQ"
    platform_type = "JOB_BOARD"
    family = "C"
