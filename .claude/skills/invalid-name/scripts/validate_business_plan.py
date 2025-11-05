#!/usr/bin/env python3
"""
Business Plan Validator

This script validates the completeness and consistency of a business plan document.
It checks for required sections, numerical consistency, and common errors.

Usage:
    python validate_business_plan.py <path_to_business_plan.md>

Options:
    --format [markdown|text]    Format of the business plan (default: markdown)
    --type [traditional|lean]   Type of business plan (default: traditional)
    --verbose                   Show detailed validation information

Example:
    python validate_business_plan.py my_business_plan.md --verbose
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional


class ValidationResult:
    """Represents a validation result with severity level."""

    def __init__(self, category: str, severity: str, message: str, line_number: Optional[int] = None):
        self.category = category
        self.severity = severity  # CRITICAL, WARNING, INFO
        self.message = message
        self.line_number = line_number

    def __str__(self):
        line_info = f" (Line {self.line_number})" if self.line_number else ""
        return f"[{self.severity}] {self.category}: {self.message}{line_info}"


class BusinessPlanValidator:
    """Validates business plan documents for completeness and consistency."""

    # Required sections for traditional business plan
    TRADITIONAL_SECTIONS = [
        "Executive Summary",
        "Company Description",
        "Market Analysis",
        "Competitive Analysis",
        "Products and Services",
        "Marketing and Sales Strategy",
        "Organization and Management",
        "Operations Plan",
        "Financial Projections",
    ]

    # Optional but recommended sections
    OPTIONAL_SECTIONS = [
        "Funding Request",
        "Risk Assessment",
        "Appendix",
    ]

    # Lean startup plan sections
    LEAN_SECTIONS = [
        "Problem",
        "Solution",
        "Key Metrics",
        "Unique Value Proposition",
        "Unfair Advantage",
        "Channels",
        "Customer Segments",
        "Cost Structure",
        "Revenue Streams",
    ]

    def __init__(self, file_path: str, plan_type: str = "traditional", verbose: bool = False):
        self.file_path = Path(file_path)
        self.plan_type = plan_type
        self.verbose = verbose
        self.content = ""
        self.lines = []
        self.results: List[ValidationResult] = []
        self.sections_found: Dict[str, bool] = {}
        self.numbers_found: Dict[str, List[float]] = {}

    def load_file(self) -> bool:
        """Load the business plan file."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
                self.lines = self.content.split('\n')
            return True
        except FileNotFoundError:
            print(f"Error: File not found: {self.file_path}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            return False

    def check_required_sections(self):
        """Check if all required sections are present."""
        required_sections = self.TRADITIONAL_SECTIONS if self.plan_type == "traditional" else self.LEAN_SECTIONS

        for section in required_sections:
            # Look for section headers (markdown ## or text)
            patterns = [
                rf"^##\s+{re.escape(section)}\s*$",
                rf"^#\s+{re.escape(section)}\s*$",
                rf"^{re.escape(section)}\s*$",
            ]

            found = False
            for i, line in enumerate(self.lines, 1):
                if any(re.match(pattern, line.strip(), re.IGNORECASE) for pattern in patterns):
                    found = True
                    self.sections_found[section] = True
                    if self.verbose:
                        self.results.append(ValidationResult(
                            "Section Check",
                            "INFO",
                            f"Found section: {section}",
                            i
                        ))
                    break

            if not found:
                self.sections_found[section] = False
                self.results.append(ValidationResult(
                    "Missing Section",
                    "CRITICAL",
                    f"Required section missing: {section}"
                ))

        # Check optional sections
        for section in self.OPTIONAL_SECTIONS:
            patterns = [
                rf"^##\s+{re.escape(section)}\s*$",
                rf"^#\s+{re.escape(section)}\s*$",
            ]

            found = any(
                any(re.match(pattern, line.strip(), re.IGNORECASE) for pattern in patterns)
                for line in self.lines
            )

            if found:
                self.sections_found[section] = True
                if self.verbose:
                    self.results.append(ValidationResult(
                        "Section Check",
                        "INFO",
                        f"Found optional section: {section}"
                    ))

    def check_executive_summary_length(self):
        """Check if executive summary is appropriately concise."""
        if "Executive Summary" not in self.sections_found or not self.sections_found["Executive Summary"]:
            return

        # Find executive summary content
        in_exec_summary = False
        exec_summary_lines = 0

        for line in self.lines:
            if re.search(r"^##?\s+Executive Summary", line, re.IGNORECASE):
                in_exec_summary = True
                continue
            elif in_exec_summary and re.match(r"^##?\s+", line):
                break
            elif in_exec_summary and line.strip():
                exec_summary_lines += 1

        # Rough estimate: ~10-15 lines per page in markdown
        estimated_pages = exec_summary_lines / 12

        if estimated_pages > 3:
            self.results.append(ValidationResult(
                "Executive Summary",
                "WARNING",
                f"Executive summary appears long (~{estimated_pages:.1f} pages). Target: 1-2 pages."
            ))
        elif estimated_pages < 0.5:
            self.results.append(ValidationResult(
                "Executive Summary",
                "WARNING",
                "Executive summary appears very short. Should be 1-2 pages with key highlights."
            ))

    def extract_numbers(self):
        """Extract monetary values and numbers from the document."""
        # Patterns for monetary values
        money_patterns = [
            (r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:million|M)', 1000000, 'million'),
            (r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:billion|B)', 1000000000, 'billion'),
            (r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', 1, 'dollars'),
            (r'€\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:million|M)', 1000000, 'million'),
            (r'€\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:billion|B)', 1000000000, 'billion'),
            (r'€\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', 1, 'euros'),
        ]

        for i, line in enumerate(self.lines, 1):
            for pattern, multiplier, unit in money_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    value_str = match.group(1).replace(',', '')
                    try:
                        value = float(value_str) * multiplier
                        context = line.strip()[:100]  # First 100 chars for context

                        # Categorize by context
                        category = "unknown"
                        context_lower = context.lower()

                        if any(word in context_lower for word in ["revenue", "sales", "income"]):
                            category = "revenue"
                        elif any(word in context_lower for word in ["profit", "ebitda", "margin"]):
                            category = "profit"
                        elif any(word in context_lower for word in ["cost", "expense", "cogs"]):
                            category = "cost"
                        elif any(word in context_lower for word in ["funding", "investment", "raise", "capital"]):
                            category = "funding"
                        elif any(word in context_lower for word in ["market", "tam", "sam", "som"]):
                            category = "market_size"

                        if category not in self.numbers_found:
                            self.numbers_found[category] = []
                        self.numbers_found[category].append(value)

                        if self.verbose:
                            self.results.append(ValidationResult(
                                "Number Extraction",
                                "INFO",
                                f"Found {category}: ${value:,.2f} - '{context}'",
                                i
                            ))
                    except ValueError:
                        pass

    def check_financial_consistency(self):
        """Check for basic financial consistency."""
        # Check if revenue numbers are consistent
        if "revenue" in self.numbers_found and len(self.numbers_found["revenue"]) > 1:
            revenues = self.numbers_found["revenue"]
            unique_revenues = set(revenues)

            if len(unique_revenues) > 1:
                # Multiple different revenue numbers - check if they're reasonably related
                min_rev = min(revenues)
                max_rev = max(revenues)

                if min_rev > 0 and max_rev / min_rev > 100:  # More than 100x difference
                    self.results.append(ValidationResult(
                        "Financial Consistency",
                        "WARNING",
                        f"Large variance in revenue numbers found: ${min_rev:,.0f} to ${max_rev:,.0f}. "
                        "Ensure Year 1 vs Year 5 projections are clearly labeled."
                    ))

        # Check if funding request is mentioned but not quantified
        funding_keywords = ["raising", "seeking", "investment", "funding request"]
        has_funding_mention = any(
            any(keyword in line.lower() for keyword in funding_keywords)
            for line in self.lines
        )

        if has_funding_mention and "funding" not in self.numbers_found:
            self.results.append(ValidationResult(
                "Funding Request",
                "WARNING",
                "Funding or investment mentioned but no specific amount found. Be specific about funding needs."
            ))

    def check_common_errors(self):
        """Check for common business plan errors."""
        content_lower = self.content.lower()

        # Check for "no competition" claims
        if any(phrase in content_lower for phrase in [
            "no competition", "no competitors", "no direct competitor"
        ]):
            self.results.append(ValidationResult(
                "Competition Analysis",
                "WARNING",
                "Document claims 'no competition'. Every business has competition (direct, indirect, or substitutes). "
                "Revise to acknowledge all forms of competition."
            ))

        # Check for vague market statements
        vague_phrases = [
            ("huge market", "Quantify market size with specific numbers (TAM/SAM/SOM)"),
            ("large opportunity", "Quantify opportunity with specific market size"),
            ("growing market", "Provide specific growth rate percentage and source"),
            ("everyone", "Define specific target customer segments instead of 'everyone'"),
        ]

        for phrase, suggestion in vague_phrases:
            if phrase in content_lower:
                self.results.append(ValidationResult(
                    "Vague Language",
                    "WARNING",
                    f"Found vague phrase: '{phrase}'. {suggestion}"
                ))

        # Check for unsupported superlatives
        superlatives = [
            "revolutionary", "groundbreaking", "disruptive", "game-changing",
            "innovative", "unique", "first-of-its-kind"
        ]

        for word in superlatives:
            if word in content_lower:
                # Count occurrences
                count = content_lower.count(word)
                if count > 2:
                    self.results.append(ValidationResult(
                        "Buzzwords",
                        "INFO",
                        f"Word '{word}' used {count} times. Ensure claims are backed by evidence, "
                        "not just superlatives."
                    ))

    def check_citations(self):
        """Check if market data and claims are cited."""
        # Look for citations or sources
        citation_patterns = [
            r'according to',
            r'source:',
            r'\[\d+\]',  # Markdown citation
            r'\(.*\d{4}.*\)',  # Year in parentheses
        ]

        has_citations = any(
            any(re.search(pattern, line, re.IGNORECASE) for pattern in citation_patterns)
            for line in self.lines
        )

        has_market_claims = any(
            word in self.content.lower()
            for word in ["market size", "market research", "industry report", "study shows", "research indicates"]
        )

        if has_market_claims and not has_citations:
            self.results.append(ValidationResult(
                "Citations",
                "WARNING",
                "Market research or data claims found but no citations detected. "
                "Cite all data sources for credibility."
            ))

    def check_plan_length(self):
        """Check if plan is appropriate length."""
        if self.plan_type == "traditional":
            # Rough estimate: ~50 lines per page
            estimated_pages = len([line for line in self.lines if line.strip()]) / 50

            if estimated_pages > 50:
                self.results.append(ValidationResult(
                    "Plan Length",
                    "WARNING",
                    f"Business plan appears very long (~{estimated_pages:.0f} pages). "
                    "Traditional plans should be 15-25 pages (+ appendix). Consider moving details to appendix."
                ))
            elif estimated_pages < 10:
                self.results.append(ValidationResult(
                    "Plan Length",
                    "WARNING",
                    f"Business plan appears short (~{estimated_pages:.0f} pages). "
                    "Ensure all required sections are adequately developed (target: 15-25 pages)."
                ))

    def validate(self) -> Tuple[bool, List[ValidationResult]]:
        """Run all validation checks."""
        if not self.load_file():
            return False, []

        # Run all checks
        self.check_required_sections()
        self.check_executive_summary_length()
        self.extract_numbers()
        self.check_financial_consistency()
        self.check_common_errors()
        self.check_citations()
        self.check_plan_length()

        # Determine overall success
        critical_count = sum(1 for r in self.results if r.severity == "CRITICAL")
        success = critical_count == 0

        return success, self.results

    def print_report(self):
        """Print validation report."""
        print("\n" + "=" * 70)
        print("BUSINESS PLAN VALIDATION REPORT")
        print("=" * 70)
        print(f"File: {self.file_path}")
        print(f"Plan Type: {self.plan_type.title()}")
        print("=" * 70 + "\n")

        # Count results by severity
        critical = [r for r in self.results if r.severity == "CRITICAL"]
        warnings = [r for r in self.results if r.severity == "WARNING"]
        info = [r for r in self.results if r.severity == "INFO"]

        # Print critical issues
        if critical:
            print("CRITICAL ISSUES:")
            print("-" * 70)
            for result in critical:
                print(f"  • {result.message}")
            print()

        # Print warnings
        if warnings:
            print("WARNINGS:")
            print("-" * 70)
            for result in warnings:
                print(f"  • {result.message}")
            print()

        # Print info (only if verbose)
        if info and self.verbose:
            print("INFORMATION:")
            print("-" * 70)
            for result in info:
                print(f"  • {result.message}")
            print()

        # Summary
        print("=" * 70)
        print("SUMMARY:")
        print(f"  Critical Issues: {len(critical)}")
        print(f"  Warnings: {len(warnings)}")
        print(f"  Info: {len(info)}")

        # Sections summary
        if self.plan_type == "traditional":
            required = self.TRADITIONAL_SECTIONS
        else:
            required = self.LEAN_SECTIONS

        found_count = sum(1 for s in required if self.sections_found.get(s, False))
        print(f"  Required Sections: {found_count}/{len(required)}")

        print("=" * 70)

        if len(critical) == 0 and len(warnings) == 0:
            print("\n✓ PASSED: Business plan validation successful!\n")
        elif len(critical) == 0:
            print(f"\n⚠ PASSED WITH WARNINGS: {len(warnings)} warnings to address.\n")
        else:
            print(f"\n✗ FAILED: {len(critical)} critical issues must be fixed.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Validate business plan for completeness and consistency",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument("file", help="Path to business plan file")
    parser.add_argument("--type", choices=["traditional", "lean"], default="traditional",
                       help="Type of business plan (default: traditional)")
    parser.add_argument("--verbose", action="store_true",
                       help="Show detailed validation information")

    args = parser.parse_args()

    validator = BusinessPlanValidator(args.file, args.type, args.verbose)
    success, results = validator.validate()
    validator.print_report()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
