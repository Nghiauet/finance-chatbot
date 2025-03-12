# adapter/database/repositories/sqlalchemy_company_repository.py
from uuid import UUID
from typing import Optional, List
from sqlalchemy.orm import Session

from domain.repositories.company_repository import CompanyRepository
from domain.models.company import Company as DomainCompany
from adapter.database.models.company import Company as DBCompany

class SQLAlchemyCompanyRepository(CompanyRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, company_id: UUID) -> Optional[DomainCompany]:
        db_company = self.session.query(DBCompany).filter(DBCompany.id == company_id).first()
        return DomainCompany.from_orm(db_company) if db_company else None

    def list_all(self) -> List[DomainCompany]:
        db_companies = self.session.query(DBCompany).all()
        return [DomainCompany.from_orm(db) for db in db_companies]

    def create(self, company: DomainCompany) -> DomainCompany:
        db_company = DBCompany(**company.dict())
        self.session.add(db_company)
        self.session.commit()
        self.session.refresh(db_company)
        return DomainCompany.from_orm(db_company)

    def delete(self, company_id: UUID) -> None:
        self.session.query(DBCompany).filter_by(id=company_id).delete()
        self.session.commit()