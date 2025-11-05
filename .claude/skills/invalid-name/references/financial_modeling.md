# Financial Projection Methodology

This document provides comprehensive guidance on creating realistic, credible financial projections for business plans.

## Core Principles

### 1. Build Bottom-Up, Not Top-Down

**Wrong Approach** (Top-Down):
- "The market is €10B, we'll capture 1%, so €100M in Year 3"
- Starts with market size and assumes capture rate
- Not credible to sophisticated readers

**Correct Approach** (Bottom-Up):
- Start with unit economics: "We'll sell 100 units in Month 1 at €50 each"
- Build up from customer acquisition: "We'll acquire 50 customers/month at €20 CAC"
- Show the math: customers × conversion rate × average order value
- Demonstrate how you'll actually achieve the numbers

### 2. Document All Assumptions

Every number in your projections must come from somewhere. Document:
- **What** the assumption is
- **Why** you believe it's realistic
- **Source** (industry data, comparable companies, pilot results, conservative estimate)
- **Benchmark** (how it compares to industry norms)

### 3. Use Industry Benchmarks

Compare your assumptions to industry standards:
- Gross margins by industry
- Customer acquisition costs by channel
- Conversion rates by business model
- Growth rates for similar companies
- Operating expense ratios

**Common Industry Benchmarks**:
- SaaS: 70-85% gross margin, Rule of 40 (growth % + profit margin % ≥ 40)
- E-commerce: 30-50% gross margin, 2-5% net margin
- Retail: 40-60% gross margin, 2-7% net margin
- Manufacturing: 25-40% gross margin, 5-15% net margin
- Services: 40-60% gross margin, 10-20% net margin

### 4. Create Multiple Scenarios

Always provide three scenarios:

**Conservative** (70% of base case):
- Slower customer acquisition
- Higher costs than expected
- Longer sales cycles
- Market headwinds
- Execution challenges

**Moderate** (Base Case):
- Most likely scenario
- Realistic assumptions
- Expected market conditions
- Default projection

**Aggressive** (130% of base case):
- Faster adoption
- Better margins
- Shorter sales cycles
- Favorable market conditions
- Strong execution

### 5. Interconnect All Statements

The three financial statements must interconnect properly:
- Net Income from Income Statement → Retained Earnings on Balance Sheet
- Net Income from Income Statement → Starting point for Cash Flow Statement
- Capital expenditures affect both Cash Flow Statement and Balance Sheet
- Debt on Balance Sheet generates Interest Expense on Income Statement

## Revenue Projections

### Step 1: Define Revenue Streams

List each way the business generates revenue:
- Product A sales
- Product B sales
- Service fees
- Subscription revenue
- Licensing fees
- Other revenue sources

### Step 2: Build Unit Economics for Each Stream

For each revenue stream, determine:

**Units Sold Projection**:
- How many units/customers in Month 1?
- How does this grow month-over-month?
- What drives the growth? (marketing spend, word-of-mouth, sales team expansion)
- What's the seasonality?
- What's the retention/churn rate?

**Price Per Unit**:
- What's the initial price?
- Any price changes over time?
- Discounts or promotions?
- Price sensitivity to volume?

**Revenue Calculation**:
```
Revenue = Units Sold × Price Per Unit
```

### Step 3: Build Customer Acquisition Model

For subscription/service businesses:
- Month 1 customers
- New customers acquired each month (by channel)
- Churn rate (monthly % who leave)
- Net customer growth
- Average revenue per customer

**Formula**:
```
Customers(month N) = Customers(month N-1) + New Customers - Churned Customers
Monthly Revenue = Customers × Average Revenue Per Customer
```

### Step 4: Growth Assumptions

Justify growth rates:
- **Early Stage** (Months 1-6): Slow, building foundation
- **Growth Phase** (Months 7-18): Accelerating as product-market fit proven
- **Scale Phase** (Year 2-5): Sustained growth but decelerating rate

**Common Growth Patterns**:
- Consumer apps: 10-30% monthly growth (early), 5-10% (later)
- SaaS: 5-15% monthly growth (early), 3-7% (later)
- E-commerce: 5-10% monthly growth (early), 2-5% (later)
- Traditional retail: 2-5% monthly growth (early), 1-3% (later)

Never project >100% growth year-over-year for more than 2-3 years without exceptional justification.

## Cost Projections

### Cost of Goods Sold (COGS)

Direct costs to produce/deliver the product or service:
- Raw materials and supplies
- Direct labor (production workers)
- Shipping and delivery
- Payment processing fees
- Hosting/infrastructure (for software)
- Cost of service delivery

**Calculate Gross Margin**:
```
Gross Profit = Revenue - COGS
Gross Margin % = (Gross Profit / Revenue) × 100
```

Target gross margins by industry:
- Software/SaaS: 75-90%
- E-commerce: 30-50%
- Retail: 40-60%
- Manufacturing: 25-40%
- Services: 50-70%

### Operating Expenses

Fixed and semi-variable costs to run the business:

**Sales & Marketing**:
- Advertising and paid marketing
- Marketing team salaries
- Sales team salaries and commissions
- Marketing tools and software
- Events and conferences
- Content creation
- Public relations

**Rule of Thumb**: 20-40% of revenue for high-growth companies, 10-20% for established businesses

**Research & Development**:
- Product development team salaries
- Software and tools
- Testing and quality assurance
- Prototyping costs

**Rule of Thumb**: 10-30% of revenue for tech companies, 5-10% for others

**General & Administrative**:
- Office rent and utilities
- Management salaries
- Accounting and legal fees
- Insurance
- Office supplies and equipment
- Administrative software
- Human resources

**Rule of Thumb**: 10-20% of revenue

### Headcount Planning

Build a detailed hiring plan:

**Format**:
| Role | Start Date | Annual Salary | Benefits (%) | Total Cost |
|------|------------|---------------|--------------|------------|
| CEO | Month 1 | €120,000 | 25% | €150,000 |
| Developer 1 | Month 1 | €80,000 | 25% | €100,000 |
| Developer 2 | Month 6 | €80,000 | 25% | €50,000 (6 months) |

**Considerations**:
- Ramp time (new hires aren't fully productive immediately)
- Benefits and taxes (typically 20-40% on top of salary)
- Contractors vs full-time employees
- Regional salary differences
- Performance-based compensation

## Key Financial Metrics

### Margin Metrics

**Gross Margin**:
```
Gross Margin % = ((Revenue - COGS) / Revenue) × 100
```
Measures profitability of core product/service before operating expenses.

**Operating Margin**:
```
Operating Margin % = (Operating Income / Revenue) × 100
```
Measures profitability after all operating expenses.

**Net Margin**:
```
Net Margin % = (Net Income / Revenue) × 100
```
Bottom-line profitability after all expenses, interest, and taxes.

### Unit Economics

**Customer Acquisition Cost (CAC)**:
```
CAC = Total Sales & Marketing Expenses / Number of New Customers Acquired
```

**Best Practice**: Calculate CAC by channel (organic, paid, referral) for better insights.

**Customer Lifetime Value (CLV)**:
```
CLV = (Average Revenue Per Customer × Gross Margin %) × Average Customer Lifespan (in months or years)
```

**For Subscription Businesses**:
```
CLV = (Average Monthly Revenue Per Customer / Monthly Churn Rate) × Gross Margin %
```

**CLV:CAC Ratio**:
```
CLV:CAC Ratio = Customer Lifetime Value / Customer Acquisition Cost
```

**Target**: Minimum 3:1 ratio (each customer generates 3x their acquisition cost)
- < 3:1: Business model may not be sustainable
- 3:1 to 5:1: Healthy, sustainable
- > 5:1: Excellent, consider investing more in growth

**Payback Period**:
```
CAC Payback Period = CAC / (Average Monthly Revenue Per Customer × Gross Margin %)
```

**Target**: < 12 months for most businesses, < 6 months for high-growth SaaS

### Cash Flow Metrics (for Startups)

**Monthly Burn Rate**:
```
Burn Rate = Monthly Operating Expenses - Monthly Revenue
```
How much cash the company consumes each month.

**Runway**:
```
Runway (in months) = Current Cash Balance / Monthly Burn Rate
```
How long the company can operate before running out of money.

**Rule of Thumb**: Maintain minimum 12-18 months runway, raise when you have 6-9 months left.

### Growth Metrics

**Month-over-Month (MoM) Growth**:
```
MoM Growth % = ((This Month - Last Month) / Last Month) × 100
```

**Year-over-Year (YoY) Growth**:
```
YoY Growth % = ((This Year - Last Year) / Last Year) × 100
```

**Compound Annual Growth Rate (CAGR)**:
```
CAGR = ((Ending Value / Beginning Value)^(1/Number of Years)) - 1
```

### Efficiency Metrics

**Rule of 40** (for SaaS):
```
Rule of 40 = Revenue Growth Rate % + Profit Margin %
```
Should be ≥ 40% (e.g., 30% growth + 10% profit margin = 40%)

**Magic Number** (for SaaS):
```
Magic Number = (Revenue This Quarter - Revenue Last Quarter) × 4 / Sales & Marketing Spend Last Quarter
```
Measures sales efficiency. Target > 0.75 (means you get $0.75+ in new ARR for every $1 spent on S&M)

## Break-Even Analysis

Calculate when the business becomes profitable (revenue = expenses).

### Fixed Costs
Costs that don't vary with sales volume:
- Rent
- Salaries (core team)
- Insurance
- Software subscriptions
- Utilities

### Variable Costs
Costs that increase with each unit sold:
- COGS per unit
- Sales commissions
- Shipping per unit
- Payment processing fees

### Break-Even Calculation

**Contribution Margin Per Unit**:
```
Contribution Margin = Price Per Unit - Variable Cost Per Unit
```

**Break-Even Point (in units)**:
```
Break-Even Units = Total Fixed Costs / Contribution Margin Per Unit
```

**Break-Even Point (in revenue)**:
```
Break-Even Revenue = Break-Even Units × Price Per Unit
```

**Time to Break-Even**:
Based on projected sales ramp, when will you reach break-even revenue?

## Scenario Planning

### Conservative Scenario (70% of Base Case)

**Assumptions**:
- Sales ramp 30% slower than expected
- Customer acquisition costs 20% higher
- Gross margins 5-10% lower (higher costs)
- Sales cycles 30% longer
- Churn rate 20% higher

**When to use**: Risk assessment, stress testing, showing downside to investors

### Moderate Scenario (Base Case)

**Assumptions**:
- Most realistic projections
- Based on best available data
- Validated against industry benchmarks
- Accounts for normal challenges
- Primary projection used

**When to use**: Primary financial projections, pitch decks, business plan

### Aggressive Scenario (130% of Base Case)

**Assumptions**:
- Sales ramp 30% faster than expected
- Customer acquisition more efficient (lower CAC)
- Gross margins 5-10% higher
- Faster market adoption
- Lower churn

**When to use**: Showing upside potential, best-case planning

## Sensitivity Analysis

Identify which variables most impact financial performance:

### Key Variables to Test
- Revenue growth rate (±10%, ±20%)
- Customer acquisition cost (±20%)
- Gross margin (±5%)
- Operating expense ratio (±10%)
- Churn rate (±20%)

### Create Sensitivity Table

Example for SaaS business:

| Scenario | Revenue Growth | Gross Margin | Year 3 Revenue | Year 3 Net Income |
|----------|----------------|--------------|----------------|-------------------|
| Base | 10% MoM | 75% | €5.0M | €0.5M |
| +Growth | 12% MoM | 75% | €7.2M | €1.2M |
| -Growth | 8% MoM | 75% | €3.5M | -€0.2M |
| +Margin | 10% MoM | 80% | €5.0M | €0.8M |
| -Margin | 10% MoM | 70% | €5.0M | €0.2M |

**Insight**: This shows which variables have the biggest impact on outcomes, helping identify priorities.

## Projection Timeframes and Detail

### Year 1: Monthly Projections
- Most detail and granularity
- Month-by-month revenue, costs, cash flow
- Track hiring plan by month
- Monitor runway closely

### Years 2-3: Quarterly Projections
- Less granular but still detailed
- Quarterly revenue, costs, profitability
- Quarterly headcount additions
- Major milestones by quarter

### Years 4-5: Annual Projections
- High-level overview
- Annual revenue and profitability
- Strategic initiatives
- Long-term vision

## Common Mistakes to Avoid

### Revenue Mistakes
- ❌ Hockey stick growth without justification
- ❌ Top-down market sizing ("1% of €10B market")
- ❌ Ignoring seasonality
- ❌ No customer acquisition model
- ❌ Overly optimistic conversion rates
- ❌ Not accounting for churn

### Cost Mistakes
- ❌ Underestimating customer acquisition costs
- ❌ Missing cost categories (legal, accounting, insurance)
- ❌ Not including founder salaries
- ❌ Forgetting taxes and benefits on salaries (20-40% additional)
- ❌ No buffer for unexpected costs
- ❌ Linear cost scaling (some costs are stepped)

### General Mistakes
- ❌ Financial statements don't interconnect
- ❌ Numbers don't match across sections
- ❌ Missing assumptions documentation
- ❌ No benchmarking to industry standards
- ❌ Only one scenario (no conservative/aggressive)
- ❌ Calculations have errors
- ❌ No sensitivity analysis
- ❌ Ignoring working capital needs
- ❌ Not explaining deviations from industry norms

## Validation Checklist

Before finalizing projections, verify:

**Revenue**:
- [ ] Built bottom-up from units/customers
- [ ] Growth rates justified and benchmarked
- [ ] Seasonality accounted for
- [ ] Churn/retention modeled (if applicable)
- [ ] All revenue streams included

**Costs**:
- [ ] COGS realistic for industry
- [ ] All operating expense categories included
- [ ] Headcount plan detailed with salaries
- [ ] Taxes and benefits included (20-40% of salary)
- [ ] One-time costs vs recurring costs separated

**Metrics**:
- [ ] Gross margin matches industry benchmarks
- [ ] CAC is realistic and justified
- [ ] CLV:CAC ratio is ≥ 3:1
- [ ] Burn rate and runway calculated (if applicable)
- [ ] Break-even analysis complete

**Statements**:
- [ ] Income statement calculates correctly
- [ ] Cash flow statement interconnects with income statement
- [ ] Balance sheet balances (Assets = Liabilities + Equity)
- [ ] All three statements are interconnected

**Scenarios**:
- [ ] Conservative, moderate, aggressive scenarios created
- [ ] Scenarios differ by 25-35% from base case
- [ ] Sensitivity analysis performed
- [ ] Key assumptions documented for each scenario

**Overall**:
- [ ] All numbers match across business plan sections
- [ ] Assumptions are documented and sourced
- [ ] Benchmarked against industry comparables
- [ ] Reviewed by financial advisor or accountant
- [ ] No calculation errors
- [ ] Conservative enough to be credible

## Tools and Resources

**Financial Modeling Tools**:
- Excel/Google Sheets with templates
- `scripts/financial_calculator.py` for metrics calculation
- Industry-specific financial models
- Financial modeling courses (Wall Street Prep, CFI)

**Data Sources for Benchmarks**:
- SaaS Capital for SaaS metrics
- First Round Capital State of Startups
- Bessemer Cloud Index
- Public company financials (for mature businesses)
- Industry trade associations
- CB Insights industry reports
- PitchBook data
- Your own pilot/early data

**When in Doubt**:
- Be conservative rather than aggressive
- Document your reasoning
- Compare to similar companies
- Get feedback from mentors/advisors
- Have an accountant review
