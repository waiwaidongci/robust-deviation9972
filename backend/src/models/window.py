from sqlalchemy import Text,JSON,ForeignKey,Double,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from ..config.database import Base
from ..utils.clock import now
class ClimateWindow(Base):
    __tablename__="climate_windows"
    id:Mapped[int]=mapped_column(primary_key=True)
    __table_args__=(UniqueConstraint("study_id","code"),)
    study_id:Mapped[int]=mapped_column(ForeignKey("archive_studies.id"))
    code:Mapped[str]
    split:Mapped[str]
    values:Mapped[dict]=mapped_column(JSON)
    note:Mapped[str]=mapped_column(Text)
