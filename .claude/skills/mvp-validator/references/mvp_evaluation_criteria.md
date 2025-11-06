# MVP Evaluation Criteria Framework

## Core Evaluation Dimensions

### 1. Problem & Market

**Problem Definition Quality**
- Is the problem clearly articulated and specific?
- What evidence suggests this is a real problem (customer interviews, usage data, market research)?
- How widespread is the problem? Who experiences it most acutely?
- Is the problem urgent or a "nice-to-have"?

**Target Customer Clarity**
- Can you name a specific customer segment (not "everyone")?
- What is their current solution or workaround?
- Why would they switch to this new solution?
- What is the addressable market size realistically?

**Differentiation & Competitive Landscape**
- What direct or indirect competitors exist?
- How is this solution different or better?
- Is the differentiation defensible, or easily copied?
- What would competitors do in response?

---

### 2. MVP Requirements Assessment

**Scope Reality Check**

| Category | Questions |
|----------|-----------|
| **Feature Set** | Are features truly "minimal" or is scope creep present? Can the core hypothesis be tested with fewer features? Are there "nice-to-have" features that should be cut? |
| **Quality Expectations** | What quality level is acceptable for MVP? Are polish/UX expectations realistic? |
| **Technical Complexity** | Are there high-risk technical bets? Do dependencies exist on third-party services, APIs, or data that might not be available? |
| **Compliance/Regulatory** | Are there legal, compliance, or regulatory requirements that could block launch? |

**MVP Definition Validation**

An MVP should:
- ✅ Test one or two core assumptions about the business
- ✅ Be buildable in the proposed timeline with available resources
- ✅ Provide enough value that early customers would use it
- ✅ Include only features necessary to validate the hypothesis

Red flags:
- ❌ "We need feature X, Y, Z, and A before any customer will use it"
- ❌ "We're rebuilding the feature for a third time because the MVP wasn't quite right"
- ❌ Months or years to first customer

**Dependency Analysis**

List all critical dependencies:
- **External APIs/Services**: What if they change pricing, availability, or terms?
- **Data Dependencies**: Can required data be obtained? What if a key data source isn't available?
- **Team Skills**: Are specialized skills (ML, complex infrastructure, regulatory expertise) required?
- **Hardware/Manufacturing**: For physical products, what is the supply chain risk?
- **Market Conditions**: Will this work if the market conditions change (recession, regulation, competitor moves)?

---

### 3. Implementation Plan Evaluation

**Timeline Realism**

General guidance (adjust based on team experience and complexity):
- Early-stage web/mobile product: 2-4 months for experienced team, 4-8 months for first-time founders
- Complex technical product: 4-8 months minimum
- Regulatory/compliance products: 6-12+ months
- Physical products: 6-18 months

**Red flags:**
- Timeline doesn't account for QA, deployment, unexpected bugs
- Estimates assume everything goes perfectly
- No buffer for unknowns
- Timeline was set arbitrarily rather than bottom-up estimated
- Same team simultaneously building platform AND finding customers

**Resource Alignment**

- Does the team have experience with similar projects?
- Are all required roles covered (engineering, product, design, ops)?
- Is someone explicitly responsible for customer discovery/validation?
- What is the realistic velocity given team size and experience?
- Are there skill gaps that need to be filled?

**Risk Identification**

Evaluate whether the plan identifies:
- **Technical risks**: Complex integrations, scaling challenges, unknown technologies
- **Market risks**: Will customers actually want this? How will we know?
- **Operational risks**: Can we deliver at the planned quality/timeline?
- **Team risks**: Do we have the skills? Will the team stay aligned?
- **External risks**: Regulatory changes, competitor moves, market conditions

Each major risk should have:
- Likelihood assessment (high/medium/low)
- Impact if it occurs
- Mitigation strategy or early signal

**Validation Strategy**

The plan should define how success/failure will be measured:
- Quantitative metrics (adoption, retention, revenue, etc.)
- Timeline for validation (when will you know if the MVP is working?)
- Pivot criteria (what would make you pivot or shutdown?)
- Learning approach (how will you talk to customers?)

---

### 4. Founder & Team Assessment

**Market/Domain Expertise**
- Do founders have relevant domain knowledge or unique insight?
- Have they talked to enough customers to validate the problem?
- Are they making this decision based on customer feedback or assumptions?

**Execution Capability**
- Have they built products before?
- Do they have relevant technical expertise, or will they need to hire?
- Track record of delivering on commitments?

**Decision-Making Quality**
- How did they arrive at these requirements/timeline?
- Are they open to feedback and iteration?
- Do they understand MVP philosophy or are they trying to build a "complete" product?

---

## Industry-Specific Considerations

### SaaS/Web Products
- User acquisition cost vs. lifetime value math (even rough estimates)
- Onboarding complexity and support burden
- Retention assumptions realistic?
- Pricing strategy validated with customers?

### Marketplace
- Supply side (can you source enough sellers/providers?)
- Demand side (can you attract enough buyers?)
- Unit economics at small scale vs. plan to scale

### Mobile Apps
- App store approval timeline (iOS especially)
- Performance/device compatibility assumptions
- Update/version management strategy

### Physical Products
- Manufacturing/supply chain realities
- Unit economics at low volume
- Distribution strategy

### AI/ML Products
- Data requirements (quality, quantity, licensing)
- Model accuracy assumptions
- Computational cost and latency
- Regulatory/ethical considerations

---

## Feedback Patterns

### Green Lights ✅
- Problem is clearly validated through customer conversations
- MVP scope is tightly focused on testing one key hypothesis
- Timeline is realistic with buffer
- Team has relevant experience
- Critical risks are identified and mitigated
- Clear success metrics defined

### Yellow Lights 🟡
- Problem is assumed rather than validated
- Scope is reasonable but a few "must-haves" could potentially be cut
- Timeline is optimistic but not impossible
- Team is strong but lacks specific experience in this domain
- Some risks identified but not all
- Success metrics are defined but somewhat vague

### Red Flags 🚩
- Problem statement is vague or unvalidated
- MVP scope includes too many features or unclear priorities
- Timeline seems impossible given team size/experience
- Team lacks relevant experience and no plan to fill gaps
- Critical risks not identified or acknowledged
- No clear way to measure success or validate assumptions
- Founders seem attached to a specific solution rather than validating the problem
