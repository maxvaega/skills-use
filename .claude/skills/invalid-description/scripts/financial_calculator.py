#!/usr/bin/env python3
"""
Financial Calculator for Business Plans

This script performs common financial calculations needed for business plan creation.
It calculates margins, ratios, unit economics, break-even points, and other key metrics.

Usage:
    python financial_calculator.py [options]

Examples:
    # Calculate gross margin
    python financial_calculator.py --revenue 500000 --cogs 200000 --calculate gross-margin

    # Calculate CLV:CAC ratio
    python financial_calculator.py --clv 15000 --cac 5000 --calculate clv-cac-ratio

    # Calculate break-even point
    python financial_calculator.py --fixed-costs 100000 --price 50 --variable-cost 20 --calculate break-even

    # Calculate burn rate and runway
    python financial_calculator.py --monthly-expenses 50000 --monthly-revenue 20000 --cash 300000 --calculate runway
"""

import argparse
import sys
from typing import Dict, Any


def calculate_gross_margin(revenue: float, cogs: float) -> Dict[str, Any]:
    """Calculate gross profit and gross margin percentage."""
    if revenue == 0:
        return {"error": "Revenue cannot be zero"}

    gross_profit = revenue - cogs
    gross_margin_pct = (gross_profit / revenue) * 100

    return {
        "revenue": f"${revenue:,.2f}",
        "cogs": f"${cogs:,.2f}",
        "gross_profit": f"${gross_profit:,.2f}",
        "gross_margin_percent": f"{gross_margin_pct:.2f}%"
    }


def calculate_operating_margin(revenue: float, operating_income: float) -> Dict[str, Any]:
    """Calculate operating margin percentage."""
    if revenue == 0:
        return {"error": "Revenue cannot be zero"}

    operating_margin_pct = (operating_income / revenue) * 100

    return {
        "revenue": f"${revenue:,.2f}",
        "operating_income": f"${operating_income:,.2f}",
        "operating_margin_percent": f"{operating_margin_pct:.2f}%"
    }


def calculate_net_margin(revenue: float, net_income: float) -> Dict[str, Any]:
    """Calculate net margin percentage."""
    if revenue == 0:
        return {"error": "Revenue cannot be zero"}

    net_margin_pct = (net_income / revenue) * 100

    return {
        "revenue": f"${revenue:,.2f}",
        "net_income": f"${net_income:,.2f}",
        "net_margin_percent": f"{net_margin_pct:.2f}%"
    }


def calculate_cac(marketing_spend: float, new_customers: int) -> Dict[str, Any]:
    """Calculate Customer Acquisition Cost (CAC)."""
    if new_customers == 0:
        return {"error": "Number of new customers cannot be zero"}

    cac = marketing_spend / new_customers

    return {
        "total_marketing_spend": f"${marketing_spend:,.2f}",
        "new_customers_acquired": new_customers,
        "customer_acquisition_cost": f"${cac:.2f}"
    }


def calculate_clv(avg_revenue_per_customer: float, gross_margin_pct: float,
                  avg_lifespan_months: float) -> Dict[str, Any]:
    """Calculate Customer Lifetime Value (CLV)."""
    clv = avg_revenue_per_customer * (gross_margin_pct / 100) * avg_lifespan_months

    return {
        "avg_revenue_per_customer_per_month": f"${avg_revenue_per_customer:.2f}",
        "gross_margin_percent": f"{gross_margin_pct:.2f}%",
        "avg_customer_lifespan_months": avg_lifespan_months,
        "customer_lifetime_value": f"${clv:.2f}"
    }


def calculate_clv_subscription(monthly_revenue: float, monthly_churn_pct: float,
                                gross_margin_pct: float) -> Dict[str, Any]:
    """Calculate CLV for subscription businesses."""
    if monthly_churn_pct == 0:
        return {"error": "Monthly churn percentage cannot be zero"}

    clv = (monthly_revenue / (monthly_churn_pct / 100)) * (gross_margin_pct / 100)
    avg_lifespan = 1 / (monthly_churn_pct / 100)

    return {
        "monthly_revenue_per_customer": f"${monthly_revenue:.2f}",
        "monthly_churn_percent": f"{monthly_churn_pct:.2f}%",
        "gross_margin_percent": f"{gross_margin_pct:.2f}%",
        "avg_customer_lifespan_months": f"{avg_lifespan:.1f}",
        "customer_lifetime_value": f"${clv:.2f}"
    }


def calculate_clv_cac_ratio(clv: float, cac: float) -> Dict[str, Any]:
    """Calculate CLV:CAC ratio."""
    if cac == 0:
        return {"error": "CAC cannot be zero"}

    ratio = clv / cac

    assessment = ""
    if ratio < 1:
        assessment = "CRITICAL: Losing money on each customer"
    elif ratio < 3:
        assessment = "WARNING: Business model may not be sustainable (target ≥3:1)"
    elif ratio <= 5:
        assessment = "HEALTHY: Sustainable business model"
    else:
        assessment = "EXCELLENT: Strong unit economics, consider investing more in growth"

    return {
        "customer_lifetime_value": f"${clv:.2f}",
        "customer_acquisition_cost": f"${cac:.2f}",
        "clv_cac_ratio": f"{ratio:.2f}:1",
        "assessment": assessment
    }


def calculate_payback_period(cac: float, monthly_revenue: float, gross_margin_pct: float) -> Dict[str, Any]:
    """Calculate CAC payback period in months."""
    if monthly_revenue == 0 or gross_margin_pct == 0:
        return {"error": "Monthly revenue and gross margin cannot be zero"}

    monthly_gross_profit = monthly_revenue * (gross_margin_pct / 100)
    payback_months = cac / monthly_gross_profit

    assessment = ""
    if payback_months <= 6:
        assessment = "EXCELLENT: Very fast payback"
    elif payback_months <= 12:
        assessment = "GOOD: Healthy payback period"
    elif payback_months <= 24:
        assessment = "ACCEPTABLE: Consider improving unit economics"
    else:
        assessment = "WARNING: Long payback period may strain cash flow"

    return {
        "customer_acquisition_cost": f"${cac:.2f}",
        "monthly_revenue_per_customer": f"${monthly_revenue:.2f}",
        "gross_margin_percent": f"{gross_margin_pct:.2f}%",
        "monthly_gross_profit_per_customer": f"${monthly_gross_profit:.2f}",
        "payback_period_months": f"{payback_months:.1f}",
        "assessment": assessment
    }


def calculate_burn_rate_runway(monthly_expenses: float, monthly_revenue: float,
                                cash_balance: float) -> Dict[str, Any]:
    """Calculate monthly burn rate and runway."""
    monthly_burn = monthly_expenses - monthly_revenue

    if monthly_burn <= 0:
        return {
            "monthly_expenses": f"${monthly_expenses:,.2f}",
            "monthly_revenue": f"${monthly_revenue:,.2f}",
            "monthly_burn_rate": "$0.00",
            "cash_balance": f"${cash_balance:,.2f}",
            "runway_months": "INFINITE",
            "status": "Cash flow positive! No burn."
        }

    runway_months = cash_balance / monthly_burn

    status = ""
    if runway_months < 6:
        status = "CRITICAL: Less than 6 months runway - raise funds immediately"
    elif runway_months < 12:
        status = "WARNING: Less than 12 months runway - start fundraising now"
    elif runway_months < 18:
        status = "ADEQUATE: Comfortable runway but monitor closely"
    else:
        status = "HEALTHY: Strong cash position"

    return {
        "monthly_expenses": f"${monthly_expenses:,.2f}",
        "monthly_revenue": f"${monthly_revenue:,.2f}",
        "monthly_burn_rate": f"${monthly_burn:,.2f}",
        "cash_balance": f"${cash_balance:,.2f}",
        "runway_months": f"{runway_months:.1f}",
        "status": status
    }


def calculate_break_even(fixed_costs: float, price_per_unit: float,
                         variable_cost_per_unit: float) -> Dict[str, Any]:
    """Calculate break-even point in units and revenue."""
    contribution_margin = price_per_unit - variable_cost_per_unit

    if contribution_margin <= 0:
        return {"error": "Price must be greater than variable cost per unit"}

    break_even_units = fixed_costs / contribution_margin
    break_even_revenue = break_even_units * price_per_unit
    contribution_margin_pct = (contribution_margin / price_per_unit) * 100

    return {
        "fixed_costs": f"${fixed_costs:,.2f}",
        "price_per_unit": f"${price_per_unit:.2f}",
        "variable_cost_per_unit": f"${variable_cost_per_unit:.2f}",
        "contribution_margin_per_unit": f"${contribution_margin:.2f}",
        "contribution_margin_percent": f"{contribution_margin_pct:.2f}%",
        "break_even_units": f"{break_even_units:,.0f}",
        "break_even_revenue": f"${break_even_revenue:,.2f}"
    }


def calculate_rule_of_40(revenue_growth_pct: float, profit_margin_pct: float) -> Dict[str, Any]:
    """Calculate Rule of 40 for SaaS companies."""
    rule_of_40 = revenue_growth_pct + profit_margin_pct

    assessment = ""
    if rule_of_40 >= 40:
        assessment = "EXCELLENT: Meets Rule of 40 benchmark"
    elif rule_of_40 >= 30:
        assessment = "GOOD: Close to Rule of 40 target"
    elif rule_of_40 >= 20:
        assessment = "ACCEPTABLE: Room for improvement"
    else:
        assessment = "WARNING: Below healthy benchmarks for SaaS"

    return {
        "revenue_growth_percent": f"{revenue_growth_pct:.2f}%",
        "profit_margin_percent": f"{profit_margin_pct:.2f}%",
        "rule_of_40_score": f"{rule_of_40:.2f}%",
        "assessment": assessment
    }


def print_results(results: Dict[str, Any], title: str):
    """Print calculation results in a formatted way."""
    print(f"\n{'=' * 60}")
    print(f"{title.upper()}")
    print(f"{'=' * 60}\n")

    for key, value in results.items():
        if key == "error":
            print(f"ERROR: {value}\n")
            return
        formatted_key = key.replace("_", " ").title()
        print(f"{formatted_key:.<40} {value}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Financial Calculator for Business Plans",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument("--calculate", required=True,
                       choices=[
                           "gross-margin", "operating-margin", "net-margin",
                           "cac", "clv", "clv-subscription", "clv-cac-ratio",
                           "payback-period", "runway", "break-even", "rule-of-40"
                       ],
                       help="Type of calculation to perform")

    # Revenue and cost parameters
    parser.add_argument("--revenue", type=float, help="Total revenue")
    parser.add_argument("--cogs", type=float, help="Cost of goods sold")
    parser.add_argument("--operating-income", type=float, help="Operating income")
    parser.add_argument("--net-income", type=float, help="Net income")

    # CAC/CLV parameters
    parser.add_argument("--marketing-spend", type=float, help="Total marketing and sales spend")
    parser.add_argument("--new-customers", type=int, help="Number of new customers acquired")
    parser.add_argument("--cac", type=float, help="Customer acquisition cost")
    parser.add_argument("--clv", type=float, help="Customer lifetime value")
    parser.add_argument("--avg-revenue", type=float, help="Average revenue per customer per month")
    parser.add_argument("--gross-margin", type=float, help="Gross margin percentage")
    parser.add_argument("--avg-lifespan", type=float, help="Average customer lifespan in months")
    parser.add_argument("--monthly-churn", type=float, help="Monthly churn percentage")

    # Burn rate parameters
    parser.add_argument("--monthly-expenses", type=float, help="Total monthly expenses")
    parser.add_argument("--monthly-revenue", type=float, help="Monthly revenue")
    parser.add_argument("--cash", type=float, help="Current cash balance")

    # Break-even parameters
    parser.add_argument("--fixed-costs", type=float, help="Total fixed costs")
    parser.add_argument("--price", type=float, help="Price per unit")
    parser.add_argument("--variable-cost", type=float, help="Variable cost per unit")

    # SaaS metrics
    parser.add_argument("--growth-rate", type=float, help="Revenue growth rate percentage")
    parser.add_argument("--profit-margin", type=float, help="Profit margin percentage")

    args = parser.parse_args()

    try:
        if args.calculate == "gross-margin":
            if args.revenue is None or args.cogs is None:
                parser.error("--revenue and --cogs are required for gross margin calculation")
            results = calculate_gross_margin(args.revenue, args.cogs)
            print_results(results, "Gross Margin Calculation")

        elif args.calculate == "operating-margin":
            if args.revenue is None or args.operating_income is None:
                parser.error("--revenue and --operating-income are required")
            results = calculate_operating_margin(args.revenue, args.operating_income)
            print_results(results, "Operating Margin Calculation")

        elif args.calculate == "net-margin":
            if args.revenue is None or args.net_income is None:
                parser.error("--revenue and --net-income are required")
            results = calculate_net_margin(args.revenue, args.net_income)
            print_results(results, "Net Margin Calculation")

        elif args.calculate == "cac":
            if args.marketing_spend is None or args.new_customers is None:
                parser.error("--marketing-spend and --new-customers are required")
            results = calculate_cac(args.marketing_spend, args.new_customers)
            print_results(results, "Customer Acquisition Cost (CAC)")

        elif args.calculate == "clv":
            if args.avg_revenue is None or args.gross_margin is None or args.avg_lifespan is None:
                parser.error("--avg-revenue, --gross-margin, and --avg-lifespan are required")
            results = calculate_clv(args.avg_revenue, args.gross_margin, args.avg_lifespan)
            print_results(results, "Customer Lifetime Value (CLV)")

        elif args.calculate == "clv-subscription":
            if args.avg_revenue is None or args.monthly_churn is None or args.gross_margin is None:
                parser.error("--avg-revenue, --monthly-churn, and --gross-margin are required")
            results = calculate_clv_subscription(args.avg_revenue, args.monthly_churn, args.gross_margin)
            print_results(results, "Customer Lifetime Value (Subscription Model)")

        elif args.calculate == "clv-cac-ratio":
            if args.clv is None or args.cac is None:
                parser.error("--clv and --cac are required")
            results = calculate_clv_cac_ratio(args.clv, args.cac)
            print_results(results, "CLV:CAC Ratio Analysis")

        elif args.calculate == "payback-period":
            if args.cac is None or args.avg_revenue is None or args.gross_margin is None:
                parser.error("--cac, --avg-revenue, and --gross-margin are required")
            results = calculate_payback_period(args.cac, args.avg_revenue, args.gross_margin)
            print_results(results, "CAC Payback Period")

        elif args.calculate == "runway":
            if args.monthly_expenses is None or args.monthly_revenue is None or args.cash is None:
                parser.error("--monthly-expenses, --monthly-revenue, and --cash are required")
            results = calculate_burn_rate_runway(args.monthly_expenses, args.monthly_revenue, args.cash)
            print_results(results, "Burn Rate and Runway Analysis")

        elif args.calculate == "break-even":
            if args.fixed_costs is None or args.price is None or args.variable_cost is None:
                parser.error("--fixed-costs, --price, and --variable-cost are required")
            results = calculate_break_even(args.fixed_costs, args.price, args.variable_cost)
            print_results(results, "Break-Even Analysis")

        elif args.calculate == "rule-of-40":
            if args.growth_rate is None or args.profit_margin is None:
                parser.error("--growth-rate and --profit-margin are required")
            results = calculate_rule_of_40(args.growth_rate, args.profit_margin)
            print_results(results, "Rule of 40 (SaaS Metric)")

    except Exception as e:
        print(f"\nError: {str(e)}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
