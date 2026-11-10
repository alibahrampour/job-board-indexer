from app.connectors.unavailable import UnavailablePlatformConnector


class NodexConnector(UnavailablePlatformConnector):
    key = "nodex"
    platform_name = "Nodex"
    platform_type = "JOB_BOARD"
    family = "C"
