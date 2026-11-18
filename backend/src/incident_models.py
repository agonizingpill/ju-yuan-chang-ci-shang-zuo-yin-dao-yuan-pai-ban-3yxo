from sqlalchemy import String,Integer,Text,ForeignKey,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base
class HouseIncident(Base):
    __tablename__='house_incidents'
    __table_args__=(CheckConstraint("severity in ('normal','high')"),CheckConstraint("state in ('open','assigned','resolved','closed')"))
    id:Mapped[int]=mapped_column(primary_key=True)
    performance_id:Mapped[int]=mapped_column(ForeignKey('performances.id'))
    zone_id:Mapped[int]=mapped_column(ForeignKey('entrance_zones.id'))
    severity:Mapped[str]=mapped_column(String(20))
    description:Mapped[str]=mapped_column(Text)
    state:Mapped[str]=mapped_column(String(20),default='open')
    assignee_id:Mapped[int|None]=mapped_column(ForeignKey('crew_assignments.id'),nullable=True)
    resolution:Mapped[str]=mapped_column(Text,default='')
    closed_by:Mapped[str|None]=mapped_column(String(100),nullable=True)
class IncidentCase(Base):
    __tablename__='incident_cases'
    __table_args__=(CheckConstraint("severity in ('normal','high')"),CheckConstraint("state in ('open','resolved','closed')"))
    id:Mapped[int]=mapped_column(primary_key=True)
    performance_id:Mapped[int]=mapped_column(ForeignKey('performances.id'))
    severity:Mapped[str]=mapped_column(String(20))
    state:Mapped[str]=mapped_column(String(20),default='open')
    coordinator_id:Mapped[int]=mapped_column(ForeignKey('crew_assignments.id'))
    resolution:Mapped[str]=mapped_column(Text,default='')
    revision:Mapped[int]=mapped_column(Integer,default=1)
    closed_by:Mapped[str|None]=mapped_column(String(100),nullable=True)
class IncidentCaseMember(Base):
    __tablename__='incident_case_members'
    id:Mapped[int]=mapped_column(primary_key=True)
    case_id:Mapped[int]=mapped_column(ForeignKey('incident_cases.id'))
    incident_id:Mapped[int]=mapped_column(ForeignKey('house_incidents.id'),unique=True)
