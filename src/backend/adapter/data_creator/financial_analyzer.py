"""
Financial Analyzer Service for analyzing financial reports.
Provides calculations of key financial metrics, ratios, and AI-powered insights.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from loguru import logger

from backend.database.models import FinancialReport
from src.backend.adapter.ai.llm_service import get_llm_service

class FinancialAnalyzer:
    """Service for analyzing financial reports and generating insights."""
    
    def __init__(self):
        """Initialize the Financial Analyzer service."""
        self.llm_service = get_llm_service()
        logger.info("Financial Analyzer service initialized")
    
    def analyze(self, financial_data: Dict[str, Any]) -> str:
        """
        Analyze financial data and generate a comprehensive report.
        
        Args:
            financial_data: Dictionary containing financial metrics
            
        Returns:
            Markdown-formatted analysis of the financial data
        """
        # Calculate key financial ratios
        ratios = self._calculate_ratios(financial_data)
        
        # Generate overall health assessment
        health_assessment = self._assess_financial_health(financial_data, ratios)
        
        # Format analysis as markdown
        analysis_md = self._format_analysis_markdown(financial_data, ratios, health_assessment)
        
        # Enhance with AI insights if possible
        enhanced_analysis = self._enhance_with_ai_insights(analysis_md, financial_data)
        
        return enhanced_analysis or analysis_md
    
    def _calculate_ratios(self, data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate key financial ratios from the provided data.
        
        Args:
            data: Financial data dictionary
            
        Returns:
            Dictionary of calculated financial ratios
        """
        ratios = {}
        
        # Ensure we have valid numeric values
        revenue = float(data.get('revenue', 0) or 0)
        assets = float(data.get('assets', 0) or 0)
        liabilities = float(data.get('liabilities', 0) or 0)
        debt = float(data.get('debt', 0) or 0)
        
        # Calculate debt-to-asset ratio
        if assets > 0:
            ratios['debt_to_asset'] = debt / assets
        else:
            ratios['debt_to_asset'] = None
            
        # Calculate debt-to-equity ratio
        equity = assets - liabilities
        if equity > 0:
            ratios['debt_to_equity'] = debt / equity
        else:
            ratios['debt_to_equity'] = None
            
        # Calculate current ratio if current assets and liabilities are available
        current_assets = float(data.get('current_assets', 0) or 0)
        current_liabilities = float(data.get('current_liabilities', 0) or 0)
        
        if current_liabilities > 0:
            ratios['current_ratio'] = current_assets / current_liabilities
        else:
            ratios['current_ratio'] = None
            
        # Return on Assets (ROA)
        net_income = float(data.get('net_income', 0) or 0)
        if assets > 0:
            ratios['roa'] = net_income / assets
        else:
            ratios['roa'] = None
            
        # Return on Equity (ROE)
        if equity > 0:
            ratios['roe'] = net_income / equity
        else:
            ratios['roe'] = None
            
        # Profit margin
        if revenue > 0:
            ratios['profit_margin'] = net_income / revenue
        else:
            ratios['profit_margin'] = None
            
        return ratios
    
    def _assess_financial_health(self, data: Dict[str, Any], ratios: Dict[str, float]) -> Dict[str, Any]:
        """
        Assess the overall financial health based on data and ratios.
        
        Args:
            data: Financial data dictionary
            ratios: Calculated financial ratios
            
        Returns:
            Financial health assessment as a dictionary
        """
        assessment = {
            'overall_health': 'Neutral',
            'strengths': [],
            'weaknesses': [],
            'recommendations': []
        }
        
        # Assess debt-to-asset ratio
        if ratios.get('debt_to_asset') is not None:
            if ratios['debt_to_asset'] < 0.3:
                assessment['strengths'].append('Low debt-to-asset ratio indicates strong asset position')
            elif ratios['debt_to_asset'] > 0.6:
                assessment['weaknesses'].append('High debt-to-asset ratio may indicate overleveraging')
                assessment['recommendations'].append('Consider strategies to reduce debt or increase assets')
        
        # Assess debt-to-equity ratio
        if ratios.get('debt_to_equity') is not None:
            if ratios['debt_to_equity'] < 1.0:
                assessment['strengths'].append('Healthy debt-to-equity ratio')
            elif ratios['debt_to_equity'] > 2.0:
                assessment['weaknesses'].append('High debt-to-equity ratio indicates significant leverage')
                assessment['recommendations'].append('Review capital structure to reduce financial risk')
        
        # Assess current ratio
        if ratios.get('current_ratio') is not None:
            if ratios['current_ratio'] > 2.0:
                assessment['strengths'].append('Strong liquidity position with high current ratio')
            elif ratios['current_ratio'] < 1.0:
                assessment['weaknesses'].append('Current ratio below 1.0 indicates potential liquidity issues')
                assessment['recommendations'].append('Improve working capital management to enhance liquidity')
        
        # Assess profitability
        if ratios.get('profit_margin') is not None:
            if ratios['profit_margin'] > 0.15:
                assessment['strengths'].append('Strong profit margin indicates efficient operations')
            elif ratios['profit_margin'] < 0.05:
                assessment['weaknesses'].append('Low profit margin may indicate operational inefficiency')
                assessment['recommendations'].append('Analyze cost structure and pricing strategy')
        
        # Determine overall health
        if len(assessment['strengths']) > len(assessment['weaknesses']):
            assessment['overall_health'] = 'Strong'
        elif len(assessment['strengths']) < len(assessment['weaknesses']):
            assessment['overall_health'] = 'Concerning'
        
        return assessment
    
    def _format_analysis_markdown(self, 
                                data: Dict[str, Any], 
                                ratios: Dict[str, float],
                                health_assessment: Dict[str, Any]) -> str:
        """
        Format financial analysis as a markdown document.
        
        Args:
            data: Financial data dictionary
            ratios: Calculated financial ratios
            health_assessment: Financial health assessment
            
        Returns:
            Markdown-formatted analysis
        """
        company_code = data.get('company_code', 'Unknown')
        report_date = data.get('report_date', datetime.now())
        if isinstance(report_date, str):
            # Parse date string if needed
            try:
                report_date = datetime.strptime(report_date, '%Y-%m-%d')
            except ValueError:
                pass
        
        # Build markdown content
        md = [
            f"# Financial Analysis Report for {company_code}",
            f"*Report date: {report_date.strftime('%B %d, %Y') if isinstance(report_date, datetime) else report_date}*",
            "",
            "## Key Financial Metrics",
            ""
        ]
        
        # Financial metrics table
        md.append("| Metric | Value (in thousands) |")
        md.append("| ------ | -------------------: |")
        for key in ['revenue', 'assets', 'liabilities', 'debt', 'net_income']:
            if key in data and data[key] is not None:
                md.append(f"| {key.replace('_', ' ').title()} | {data[key]:,.2f} |")
        md.append("")
        
        # Financial ratios section
        md.append("## Financial Ratios")
        md.append("")
        md.append("| Ratio | Value | Industry Benchmark |")
        md.append("| ----- | ----: | -----------------: |")
        ratio_benchmarks = {
            'debt_to_asset': 0.4,
            'debt_to_equity': 1.5,
            'current_ratio': 2.0,
            'roa': 0.05,
            'roe': 0.12,
            'profit_margin': 0.10
        }
        ratio_display_names = {
            'debt_to_asset': 'Debt to Asset',
            'debt_to_equity': 'Debt to Equity',
            'current_ratio': 'Current Ratio',
            'roa': 'Return on Assets',
            'roe': 'Return on Equity',
            'profit_margin': 'Profit Margin'
        }
        
        for key, name in ratio_display_names.items():
            if key in ratios and ratios[key] is not None:
                md.append(f"| {name} | {ratios[key]:.3f} | {ratio_benchmarks.get(key, 'N/A')} |")
        md.append("")
        
        # Financial health assessment
        md.append("## Financial Health Assessment")
        md.append("")
        md.append(f"**Overall Financial Health**: {health_assessment['overall_health']}")
        md.append("")
        
        if health_assessment['strengths']:
            md.append("### Strengths")
            for strength in health_assessment['strengths']:
                md.append(f"- {strength}")
            md.append("")
        
        if health_assessment['weaknesses']:
            md.append("### Areas of Concern")
            for weakness in health_assessment['weaknesses']:
                md.append(f"- {weakness}")
            md.append("")
        
        if health_assessment['recommendations']:
            md.append("### Recommendations")
            for rec in health_assessment['recommendations']:
                md.append(f"- {rec}")
            md.append("")
        
        # Trend analysis placeholder
        md.append("## Trend Analysis")
        md.append("")
        md.append("*Trend analysis requires historical data which is not available in this analysis.*")
        md.append("")
        
        # Return formatted markdown
        return "\n".join(md)
    
    def _enhance_with_ai_insights(self, analysis_md: str, data: Dict[str, Any]) -> Optional[str]:
        """
        Enhance analysis with AI-generated insights using Gemini.
        
        Args:
            analysis_md: Base markdown analysis
            data: Financial data dictionary
            
        Returns:
            Enhanced analysis with AI insights or None if enhancement failed
        """
        try:
            # Create a prompt for the LLM
            prompt = f"""
            You are a financial analysis expert. I have a financial report with the following data:
            
            Company Code: {data.get('company_code', 'Unknown')}
            Revenue: {data.get('revenue', 'N/A')}
            Assets: {data.get('assets', 'N/A')}
            Liabilities: {data.get('liabilities', 'N/A')}
            Debt: {data.get('debt', 'N/A')}
            
            Here is my current analysis:
            
            {analysis_md}
            
            Please enhance this analysis with deeper insights, particularly:
            1. Any industry-specific considerations
            2. Potential business risks not covered
            3. Strategic recommendations based on the financial position
            4. Any economic factors that might impact this company
            
            Return the enhanced analysis in markdown format, keeping the current structure but adding new sections or enhancing existing ones.
            """
            
            # Generate enhanced analysis
            enhanced_analysis = self.llm_service.generate_content(
                prompt=prompt,
                system_instruction="You are a financial analysis expert with deep knowledge of financial statements, ratios, and business strategy. Provide clear, actionable insights based on financial data."
            )
            
            return enhanced_analysis
            
        except Exception as e:
            logger.error(f"Error enhancing analysis with AI: {str(e)}")
            return None
    
    def compare_reports(self, reports: List[FinancialReport]) -> str:
        """
        Compare multiple financial reports and identify trends.
        
        Args:
            reports: List of financial reports to compare
            
        Returns:
            Markdown-formatted comparative analysis
        """
        if not reports or len(reports) < 2:
            return "Insufficient reports for comparison. At least 2 reports are required."
        
        # Sort reports by date
        sorted_reports = sorted(reports, key=lambda r: r.report_date)
        
        # Extract key metrics for comparison
        metrics = ['revenue', 'assets', 'liabilities', 'debt']
        comparison_data = {}
        
        for metric in metrics:
            comparison_data[metric] = []
            for report in sorted_reports:
                value = getattr(report, metric, None)
                comparison_data[metric].append(value)
        
        # Calculate growth rates
        growth_rates = self._calculate_growth_rates(sorted_reports, metrics)
        
        # Format comparison as markdown
        return self._format_comparison_markdown(sorted_reports, comparison_data, growth_rates)
    
    def _calculate_growth_rates(self, 
                              reports: List[FinancialReport], 
                              metrics: List[str]) -> Dict[str, List[float]]:
        """
        Calculate growth rates between sequential reports.
        
        Args:
            reports: Sorted list of financial reports
            metrics: List of metrics to calculate growth for
            
        Returns:
            Dictionary of growth rates for each metric
        """
        growth_rates = {metric: [] for metric in metrics}
        
        for i in range(1, len(reports)):
            for metric in metrics:
                prev_value = getattr(reports[i-1], metric, 0) or 0
                curr_value = getattr(reports[i], metric, 0) or 0
                
                if prev_value > 0:
                    growth = (curr_value - prev_value) / prev_value
                    growth_rates[metric].append(growth)
                else:
                    growth_rates[metric].append(None)
        
        return growth_rates
    
    def _format_comparison_markdown(self, 
                                  reports: List[FinancialReport],
                                  comparison_data: Dict[str, List[Any]],
                                  growth_rates: Dict[str, List[float]]) -> str:
        """
        Format comparison analysis as markdown.
        
        Args:
            reports: List of financial reports
            comparison_data: Dictionary of metric values
            growth_rates: Dictionary of growth rates
            
        Returns:
            Markdown-formatted comparison
        """
        company_code = reports[0].company_code
        
        md = [
            f"# Financial Trend Analysis for {company_code}",
            f"*Covering period: {reports[0].report_date.strftime('%B %Y')} to {reports[-1].report_date.strftime('%B %Y')}*",
            "",
            "## Metric Trends",
            ""
        ]
        
        # Create headers for the metrics table
        headers = ["Metric"]
        for report in reports:
            headers.append(report.report_date.strftime("%b %Y"))
        
        md.append("| " + " | ".join(headers) + " |")
        md.append("| " + " | ".join(["---" for _ in range(len(headers))]) + " |")
        
        # Add data rows
        for metric in comparison_data:
            row = [metric.capitalize()]
            for value in comparison_data[metric]:
                row.append(f"{value:,.2f}" if value is not None else "N/A")
            md.append("| " + " | ".join(row) + " |")
        
        md.append("")
        md.append("## Growth Analysis")
        md.append("")
        
        # Create growth rate table
        growth_headers = ["Metric"]
        for i in range(1, len(reports)):
            period = f"{reports[i-1].report_date.strftime('%b %Y')} to {reports[i].report_date.strftime('%b %Y')}"
            growth_headers.append(period)
        
        md.append("| " + " | ".join(growth_headers) + " |")
        md.append("| " + " | ".join(["---" for _ in range(len(growth_headers))]) + " |")
        
        # Add growth rate rows
        for metric in growth_rates:
            row = [metric.capitalize()]
            for rate in growth_rates[metric]:
                if rate is not None:
                    row.append(f"{rate:.2%}")
                else:
                    row.append("N/A")
            md.append("| " + " | ".join(row) + " |")
        
        return "\n".join(md)
