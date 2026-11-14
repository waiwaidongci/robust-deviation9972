from sqlalchemy import Text,JSON,ForeignKey,Double,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from ..config.database import Base
from ..utils.clock import now
class FeatureSpec(Base):
    __tablename__="feature_specs"
    id:Mapped[int]=mapped_column(primary_key=True)
    __table_args__=(UniqueConstraint("study_id","code"),UniqueConstraint("study_id","position"))
    study_id:Mapped[int]=mapped_column(ForeignKey("archive_studies.id"))
    code:Mapped[str]
    label:Mapped[str]
    unit:Mapped[str]
    position:Mapped[int]
    meaning:Mapped[str]=mapped_column(Text)
