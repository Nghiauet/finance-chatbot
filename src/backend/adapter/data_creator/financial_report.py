from datetime import datetime
from typing import Optional
from decimal import Decimal

class FinancialReport:
    def __init__(
        self,
        report_id: str,
        company_name: str,
        period: str,
        revenue: Decimal,
        expenses: Decimal,
        assets: Optional[Decimal] = None,
        liabilities: Optional[Decimal] = None
    ):
        if revenue < 0 or expenses < 0:
            raise ValueError("Revenue and expenses must be positive values")
            
        self.report_id = report_id
        self.company_name = company_name
        self.period = self._validate_period(period)
        self.revenue = revenue
        self.expenses = expenses
        self.assets = assets
        self.liabilities = liabilities

    def _validate_period(self, period: str) -> str:
        try:
            datetime.strptime(period, "%Y-%m")
            return period
        except ValueError:
            raise ValueError("Period must be in YYYY-MM format")

    @property
    def net_income(self) -> Decimal:
        return self.revenue - self.expenses

    @property
    def profit_margin(self) -> Decimal:
        if self.revenue == 0:
            return Decimal(0)
        return (self.net_income / self.revenue).quantize(Decimal('0.01'))

    @property
    def debt_to_equity_ratio(self) -> Optional[Decimal]:
        if self.assets is None or self.liabilities is None:
            return None
        if self.assets == 0:
            return Decimal(0)
        return (self.liabilities / self.assets).quantize(Decimal('0.01'))

    def is_profitable(self) -> bool:
        return self.net_income > 0

    def update_revenue(self, new_revenue: Decimal) -> None:
        if new_revenue < 0:
            raise ValueError("Revenue cannot be negative")
        self.revenue = new_revenue 