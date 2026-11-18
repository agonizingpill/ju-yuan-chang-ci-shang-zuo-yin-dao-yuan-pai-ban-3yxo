from fastapi import HTTPException
from sqlalchemy import select
from .incident_models import HouseIncident,IncidentCase,IncidentCaseMember
from .staff_models import CrewAssignment
from .models import CrewCall
from .zones_service import performance_context
from .staff_service import locked
from .services import pack,audit
from . import incidents_service as incidents

def case_view(s,x):
    a=s.get(CrewAssignment,x.coordinator_id)
    members=s.scalars(select(IncidentCaseMember).where(IncidentCaseMember.case_id==x.id).order_by(IncidentCaseMember.id)).all()
    return pack(x)|{'coordinator_name':a.staff_name,'coordinator_code':a.staff_code,'members':[incidents.view(s,s.get(HouseIncident,m.incident_id)) for m in members]}
def lock_case(s,id):
    x=s.scalar(select(IncidentCase).where(IncidentCase.id==id).with_for_update().execution_options(populate_existing=True))
    if not x:raise HTTPException(404,'事件宗不存在')
    return x
def lock_incidents(s,ids):
    rows=s.scalars(select(HouseIncident).where(HouseIncident.id.in_(sorted(set(ids)))).with_for_update().execution_options(populate_existing=True)).all() if ids else []
    if len(rows)!=len(set(ids)):raise HTTPException(404,'事件不存在')
    return rows
def check_mergeable(s,x,performance_id):
    if x.performance_id!=performance_id:raise HTTPException(409,'只能归宗同一场次的事件')
    if x.state=='closed':raise HTTPException(409,f'事件 #{x.id} 已关闭，不能归宗')
    if incidents.member_of(s,x.id):raise HTTPException(409,f'事件 #{x.id} 已归宗，不能重复归宗')
def severity_of(rows):return 'high' if any(x.severity=='high' for x in rows) else 'normal'
def create(s,d,u):
    c,p,prod=performance_context(s,d.performance_id)
    a=locked(s,CrewAssignment,d.coordinator_id);call=s.get(CrewCall,a.crew_call_id)
    if call.performance_id!=p.id or not a.checked_in:raise HTTPException(409,'统筹人须是本场已实名到岗人员')
    ids=list(dict.fromkeys(d.incident_ids))
    if len(ids)<2:raise HTTPException(409,'至少选择两条不同的未关闭事件归宗')
    rows=lock_incidents(s,ids)
    for x in rows:check_mergeable(s,x,p.id)
    case=IncidentCase(performance_id=p.id,coordinator_id=a.id,severity=severity_of(rows));s.add(case);s.flush()
    for x in rows:s.add(IncidentCaseMember(case_id=case.id,incident_id=x.id))
    s.flush();audit(s,u,f'归宗整案 #{case.id} 合并{len(rows)}条事件');return case_view(s,case)
def append(s,id,d,u):
    case=lock_case(s,id)
    if case.state=='closed':raise HTTPException(409,'事件宗已结案，不能追加事件')
    ids=list(dict.fromkeys(d.incident_ids))
    if not ids:raise HTTPException(409,'请选择要追加的未归宗事件')
    rows=lock_incidents(s,ids)
    for x in rows:check_mergeable(s,x,case.performance_id)
    for x in rows:s.add(IncidentCaseMember(case_id=case.id,incident_id=x.id))
    s.flush()
    members=s.scalars(select(IncidentCaseMember).where(IncidentCaseMember.case_id==case.id)).all()
    case.severity=severity_of([s.get(HouseIncident,m.incident_id) for m in members])
    if case.state=='resolved':case.state='open'
    case.revision+=1;audit(s,u,f'追加{len(rows)}条事件入宗 #{id}，原结案核对失效');return case_view(s,case)
def resolve(s,id,d,u):
    case=lock_case(s,id)
    if case.state=='closed':raise HTTPException(409,'事件宗已结案，不能重复处置')
    if len(d.resolution.strip())<8:raise HTTPException(409,'处置说明至少8字')
    case.resolution=d.resolution.strip();case.state='resolved';case.revision+=1;audit(s,u,f'登记整宗处置 #{id}');return case_view(s,case)
def close(s,id,d,u):
    case=lock_case(s,id)
    if case.state=='closed':raise HTTPException(409,'事件宗已结案，不能重复结案')
    if case.revision!=d.expected_revision:raise HTTPException(409,'事件宗已有新的变更，原结案核对失效，请刷新后按当前成员结案')
    if case.state!='resolved':raise HTTPException(409,'须先登记整宗处置说明，经理再结案')
    members=s.scalars(select(IncidentCaseMember).where(IncidentCaseMember.case_id==case.id)).all()
    rows=lock_incidents(s,[m.incident_id for m in members])
    for x in rows:x.state='closed';x.closed_by=u.email
    case.state='closed';case.closed_by=u.email;case.revision+=1;audit(s,u,f'经理整宗结案 #{id} 同步关闭{len(rows)}条事件');return case_view(s,case)
