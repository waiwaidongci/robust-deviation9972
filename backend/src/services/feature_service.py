from ..models import FeatureSpec
from ..utils.serialize import record
from .study_service import get_study

def list_features(db,sid):get_study(db,sid);return [record(f) for f in db.query(FeatureSpec).filter_by(study_id=sid).order_by(FeatureSpec.position)]
