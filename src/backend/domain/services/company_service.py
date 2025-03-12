class CompanyService:
    def __init__(self, company_repo: CompanyRepository):
        self.company_repo = company_repo  # Interface injected

    def get_company_name(self, company_id):
        company = self.company_repo.get_by_id(company_id)
        return company.name if company else None