from app.connectors.unavailable import UnavailablePlatformConnector


class OracleRecruitingConnector(UnavailablePlatformConnector):
    key = "oracle_recruiting"
    platform_name = "Oracle Recruiting"
    family = "B"
