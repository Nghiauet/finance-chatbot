from mongoengine import Document, FloatField, StringField, DateTimeField
from datetime import datetime

class FinancialReport(Document):
    company_code = StringField(required=True)
    report_date = DateTimeField(default=datetime.now)
    revenue = FloatField()
    debt = FloatField()
    liabilities = FloatField()
    assets = FloatField()
    
    meta = {
        'collection': 'financial_reports',
        'indexes': ['company_code', 'report_date']
    } 