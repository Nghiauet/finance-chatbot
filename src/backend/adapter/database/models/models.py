from sqlalchemy import Column, String, Numeric, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class FinancialReport(Base):
    __tablename__ = 'financial_reports'
    
    id = Column(String, primary_key=True)
    company_name = Column(String, nullable=False)
    period = Column(String, nullable=False)  # YYYY-MM format
    revenue = Column(Numeric(20, 2), nullable=False)
    expenses = Column(Numeric(20, 2), nullable=False)
    assets = Column(Numeric(20, 2))
    liabilities = Column(Numeric(20, 2))
    metadata = Column(JSON)  # For storing additional unstructured data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    analyses = relationship("FinancialAnalysis", back_populates="report")
    conversations = relationship("ChatConversation", back_populates="report")

class FinancialAnalysis(Base):
    __tablename__ = 'financial_analyses'
    
    id = Column(String, primary_key=True)
    report_id = Column(String, ForeignKey('financial_reports.id'))
    metrics = Column(JSON)  # Stores calculated metrics
    insights = Column(JSON)  # AI-generated insights
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    report = relationship("FinancialReport", back_populates="analyses")

class ChatConversation(Base):
    __tablename__ = 'chat_conversations'
    
    id = Column(String, primary_key=True)
    report_id = Column(String, ForeignKey('financial_reports.id'))
    messages = Column(JSON)  # Stores conversation history
    context = Column(JSON)  # Additional context for the conversation
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    report = relationship("FinancialReport", back_populates="conversations")

class AIProcessingLog(Base):
    __tablename__ = 'ai_processing_logs'
    
    id = Column(String, primary_key=True)
    report_id = Column(String, ForeignKey('financial_reports.id'))
    process_type = Column(String)  # e.g., "text_extraction", "analysis"
    status = Column(String)  # e.g., "pending", "success", "failed"
    input_data = Column(JSON)
    output_data = Column(JSON)
    error_log = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow) 