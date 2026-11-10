from app.connectors.unavailable import UnavailablePlatformConnector


class CareerSiteCloudConnector(UnavailablePlatformConnector):
    key = "careersitecloud"
    platform_name = "CareerSiteCloud"
    platform_type = "JOB_BOARD"
    family = "C"
