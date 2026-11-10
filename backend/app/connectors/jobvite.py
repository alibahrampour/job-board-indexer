from app.connectors.unavailable import UnavailablePlatformConnector


class JobviteConnector(UnavailablePlatformConnector):
    key = "jobvite"
    platform_name = "Jobvite"
    family = "C"
