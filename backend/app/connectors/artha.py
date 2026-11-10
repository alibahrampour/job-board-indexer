from app.connectors.unavailable import UnavailablePlatformConnector


class ArthaConnector(UnavailablePlatformConnector):
    key = "artha"
    platform_name = "Artha"
    platform_type = "JOB_BOARD"
    family = "C"
