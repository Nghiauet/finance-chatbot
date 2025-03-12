from abc import ABC, abstractmethod
from typing import Optional
from domain.models.financial_report import FinancialReport

class FinancialReportRepository(ABC):
    @abstractmethod
    def get_by_id(self, report_id: str) -> Optional[FinancialReport]:
        pass

    @abstractmethod
    def save(self, report: FinancialReport) -> None:
        pass

    async def save(self, report: FinancialReport):
        # Implementation of save logic
        await report.save() 