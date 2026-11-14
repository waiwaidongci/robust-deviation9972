from sqlalchemy import Text,JSON,ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from ..config.database import Base
from ..utils.clock import now
class WindowRetraction(Base):
    __tablename__="window_retractions"
    id:Mapped[int]=mapped_column(primary_key=True)
    window_id:Mapped[int]=mapped_column(ForeignKey("climate_windows.id"),unique=True)
    study_id:Mapped[int]=mapped_column(ForeignKey("archive_studies.id"))
    code:Mapped[str]
    split:Mapped[str]
    reason:Mapped[str]=mapped_column(Text)
    fingerprint:Mapped[str]
    stats:Mapped[dict]=mapped_column(JSON,default=dict)
    status:Mapped[str]=mapped_column(default="pending")
    progress:Mapped[dict]=mapped_column(JSON,default=dict)
    actor:Mapped[str]=mapped_column(default="")
    created_at:Mapped[str]=mapped_column(default=now)
