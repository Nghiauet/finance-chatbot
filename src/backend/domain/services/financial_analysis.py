class FinancialAnalysisService:
    def __init__(self, report_repository):
        self.report_repository = report_repository

    def analyze_report(self, report_id: str) -> dict:
        report = self.report_repository.get_by_id(report_id)
        return {
            'net_income': report.net_income(),
            'profit_margin': report.net_income() / report.revenue if report.revenue else 0
        } 