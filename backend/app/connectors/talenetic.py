from app.connectors.unavailable import UnavailablePlatformConnector


class TaleneticConnector(UnavailablePlatformConnector):
    key = "talenetic"
    platform_name = "Talenetic"
    platform_type = "JOB_BOARD"
    family = "C"
