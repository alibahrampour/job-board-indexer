from app.connectors.unavailable import UnavailablePlatformConnector


class ApplicantProConnector(UnavailablePlatformConnector):
    key = "applicantpro"
    platform_name = "ApplicantPro"
    family = "C"
