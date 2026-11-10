from app.connectors.unavailable import UnavailablePlatformConnector


class ZohoRecruitConnector(UnavailablePlatformConnector):
    key = "zoho_recruit"
    platform_name = "Zoho Recruit"
    family = "C"
