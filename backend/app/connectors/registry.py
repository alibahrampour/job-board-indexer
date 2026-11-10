from app.connectors.base import BaseConnector
from app.connectors.adp import ADPConnector
from app.connectors.applicantpro import ApplicantProConnector
from app.connectors.artha import ArthaConnector
from app.connectors.ashby import AshbyConnector
from app.connectors.avature import AvatureConnector
from app.connectors.bamboohr import BambooHRConnector
from app.connectors.brassring import BrassRingConnector
from app.connectors.breezy import BreezyConnector
from app.connectors.careerplug import CareerPlugConnector
from app.connectors.careersitecloud import CareerSiteCloudConnector
from app.connectors.comeet import ComeetConnector
from app.connectors.csod import CSODConnector
from app.connectors.dayforce import DayforceConnector
from app.connectors.deel import DeelConnector
from app.connectors.dover import DoverConnector
from app.connectors.eightfold_ai import EightfoldAIConnector
from app.connectors.ejobboard import EJobBoardConnector
from app.connectors.ejobsitesoftware_com import EJobsiteSoftwareComConnector
from app.connectors.firststage import FirstStageConnector
from app.connectors.freshteam import FreshteamConnector
from app.connectors.gem_com import GemComConnector
from app.connectors.gohire import GoHireConnector
from app.connectors.greenhouse import GreenhouseConnector
from app.connectors.hibob import HiBobConnector
from app.connectors.hirebridge import HireBridgeConnector
from app.connectors.hirehive import HireHiveConnector
from app.connectors.hireology import HireologyConnector
from app.connectors.hiringthing import HiringThingConnector
from app.connectors.icims import ICIMSConnector
from app.connectors.isolvedhire import ISolvedHireConnector
from app.connectors.jazzhr import JazzHRConnector
from app.connectors.jboard_io import JBoardIOConnector
from app.connectors.jobboard_com import JobBoardComConnector
from app.connectors.jobboard_io import JobBoardIOConnector
from app.connectors.jobboardfire import JobBoardFireConnector
from app.connectors.jobboardhq import JobBoardHQConnector
from app.connectors.jobboardly import JobboardlyConnector
from app.connectors.jobboardsoftware_com import JobBoardSoftwareComConnector
from app.connectors.jobkit import JobKitConnector
from app.connectors.jobmount import JobMountConnector
from app.connectors.jobiqo import JobiqoConnector
from app.connectors.jobvite import JobviteConnector
from app.connectors.join_com import JoinComConnector
from app.connectors.kula_ai import KulaAIConnector
from app.connectors.lever import LeverConnector
from app.connectors.manatal import ManatalConnector
from app.connectors.niceboard import NiceboardConnector
from app.connectors.nodex import NodexConnector
from app.connectors.oracle_recruiting import OracleRecruitingConnector
from app.connectors.pageup import PageUpConnector
from app.connectors.paradox import ParadoxConnector
from app.connectors.paycom import PaycomConnector
from app.connectors.paycor import PaycorConnector
from app.connectors.paylocity import PaylocityConnector
from app.connectors.personio import PersonioConnector
from app.connectors.phenom_people import PhenomPeopleConnector
from app.connectors.pinpoint import PinpointConnector
from app.connectors.polymer import PolymerConnector
from app.connectors.recooty import RecootyConnector
from app.connectors.recruitee import RecruiteeConnector
from app.connectors.rippling import RipplingConnector
from app.connectors.rival import RivalConnector
from app.connectors.sap_successfactors import SAPSuccessFactorsConnector
from app.connectors.smartjobboard import SmartJobBoardConnector
from app.connectors.smartrecruiters import SmartRecruitersConnector
from app.connectors.talenetic import TaleneticConnector
from app.connectors.taleo import TaleoConnector
from app.connectors.talentreef import TalentReefConnector
from app.connectors.teamtailor import TeamtailorConnector
from app.connectors.trakstar import TrakstarConnector
from app.connectors.trinet import TriNetConnector
from app.connectors.ultipro import UltiProConnector
from app.connectors.werecruit import WeRecruitConnector
from app.connectors.wiley_madgex import WileyMadgexConnector
from app.connectors.workable import WorkableConnector
from app.connectors.workday import WorkdayConnector
from app.connectors.wp_job_manager import WPJobManagerConnector
from app.connectors.zoho_recruit import ZohoRecruitConnector

_CONNECTOR_CLASSES = (
    ADPConnector,
    ApplicantProConnector,
    ArthaConnector,
    AshbyConnector,
    AvatureConnector,
    BambooHRConnector,
    BrassRingConnector,
    BreezyConnector,
    CareerPlugConnector,
    CareerSiteCloudConnector,
    ComeetConnector,
    CSODConnector,
    DayforceConnector,
    DeelConnector,
    DoverConnector,
    EightfoldAIConnector,
    EJobBoardConnector,
    EJobsiteSoftwareComConnector,
    FirstStageConnector,
    FreshteamConnector,
    GemComConnector,
    GoHireConnector,
    GreenhouseConnector,
    HiBobConnector,
    HireBridgeConnector,
    HireHiveConnector,
    HireologyConnector,
    HiringThingConnector,
    ICIMSConnector,
    ISolvedHireConnector,
    JazzHRConnector,
    JBoardIOConnector,
    JobBoardComConnector,
    JobBoardIOConnector,
    JobBoardFireConnector,
    JobBoardHQConnector,
    JobboardlyConnector,
    JobBoardSoftwareComConnector,
    JobKitConnector,
    JobMountConnector,
    JobiqoConnector,
    JobviteConnector,
    JoinComConnector,
    KulaAIConnector,
    LeverConnector,
    ManatalConnector,
    NiceboardConnector,
    NodexConnector,
    OracleRecruitingConnector,
    PageUpConnector,
    ParadoxConnector,
    PaycomConnector,
    PaycorConnector,
    PaylocityConnector,
    PersonioConnector,
    PhenomPeopleConnector,
    PinpointConnector,
    PolymerConnector,
    RecootyConnector,
    RecruiteeConnector,
    RipplingConnector,
    RivalConnector,
    SAPSuccessFactorsConnector,
    SmartJobBoardConnector,
    SmartRecruitersConnector,
    TaleneticConnector,
    TaleoConnector,
    TalentReefConnector,
    TeamtailorConnector,
    TrakstarConnector,
    TriNetConnector,
    UltiProConnector,
    WeRecruitConnector,
    WileyMadgexConnector,
    WorkableConnector,
    WorkdayConnector,
    WPJobManagerConnector,
    ZohoRecruitConnector,
)

CONNECTORS = {connector.key: connector for connector in _CONNECTOR_CLASSES}


def get_connector_class(key: str) -> type[BaseConnector]:
    try:
        return CONNECTORS[key]
    except KeyError:
        raise ValueError(f"Unknown connector '{key}'. Available: {sorted(CONNECTORS)}")
