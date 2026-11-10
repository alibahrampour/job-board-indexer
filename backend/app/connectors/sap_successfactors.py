from app.connectors.unavailable import UnavailablePlatformConnector


class SAPSuccessFactorsConnector(UnavailablePlatformConnector):
    key = "sap_successfactors"
    platform_name = "SAP SuccessFactors"
    family = "C"
