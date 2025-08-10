
UK_FOOTBALL_FINANCIAL_CONFIG = {
    "document_type": "uk_football_club_financial_statement",
    
    # Enhanced identification patterns based on research
    "identification_patterns": [
        # Company structure indicators
        "Annual Report and Financial Statements",
        "Companies House",
        "Football Club Limited",
        "AFC Limited", 
        "FC Limited",
        "City Football Club",
        "United Football Club",
        "Town Football Club",
        "Association Football Club",
        
        # UK accounting standards
        "FRS 102",
        "United Kingdom Generally Accepted Accounting Practice",
        "UK GAAP",
        "Financial Reporting Standard applicable in the UK",
        "Financial Reporting Standard 102",
        
        # UK Companies Act references
        "Companies Act 2006",
        "section 477",
        "section 476", 
        "section 393",
        "small companies regime",
        "audit exemption",
        "true and fair view",
        
        # Financial statements
        "Profit and Loss Account",
        "Balance Sheet",
        "Statement of Comprehensive Income",
        "Statement of Financial Position",
        "Statement of Changes in Equity",
        "Statement of Cash Flows",
        "Directors' Report",
        "Strategic Report",
        "Independent Auditor's Report",
        
        # Football-specific financial terms
        "matchday revenue",
        "broadcasting revenue",
        "commercial revenue",
        "player registrations",
        "player trading",
        "agent fees",
        "gate receipts",
        "prize money"
    ],
    
    # Document structure patterns for UK statements
    "document_structure": {
        "expected_order": [
            "Company Information",
            "Contents",
            "Strategic Report",
            "Directors' Report", 
            "Independent Auditor's Report",
            "Profit and Loss Account",
            "Statement of Comprehensive Income",
            "Balance Sheet",
            "Statement of Changes in Equity",
            "Statement of Cash Flows",
            "Notes to the Financial Statements"
        ],
        "section_identifiers": {
            "profit_loss": {
                "start_patterns": [
                    "PROFIT AND LOSS ACCOUNT",
                    "STATEMENT OF COMPREHENSIVE INCOME",
                    "FOR THE YEAR ENDED"
                ],
                "end_patterns": [
                    "The notes on pages",
                    "See accompanying notes",
                    "The profit and loss account has been prepared"
                ],
                "line_items_order": [
                    "Turnover",
                    "Cost of sales",
                    "Gross profit/(loss)",
                    "Administrative expenses",
                    "Operating profit/(loss)",
                    "Interest receivable",
                    "Interest payable",
                    "Profit/(loss) before taxation",
                    "Tax on loss",
                    "Loss for the financial year"
                ]
            },
            "balance_sheet": {
                "start_patterns": [
                    "BALANCE SHEET",
                    "STATEMENT OF FINANCIAL POSITION",
                    "AS AT 30 JUNE",
                    "AS AT 31"
                ],
                "key_sections": [
                    "Fixed assets",
                    "Current assets",
                    "Creditors: amounts falling due within one year",
                    "Net current liabilities",
                    "Total assets less current liabilities",
                    "Creditors: amounts falling due after more than one year",
                    "Net assets",
                    "Net liabilities",
                    "Capital and reserves"
                ]
            },
            "notes": {
                "start_patterns": [
                    "NOTES TO THE FINANCIAL STATEMENTS",
                    "NOTES TO THE ACCOUNTS",
                    "FOR THE YEAR ENDED"
                ],
                "important_notes": [
                    "Turnover",
                    "Turnover and other revenue",
                    "Turnover analysed by class of business",
                    "Operating loss",
                    "Intangible fixed assets",
                    "Tangible fixed assets",
                    "Debtors",
                    "Creditors",
                    "Related party transactions"
                ]
            }
        }
    },
    
    # Enhanced number format recognition for UK accounting
    "number_formats": {
        "negative_indicators": ["()", "parentheses", "brackets"],
        "negative_patterns": [
            r"\(£?[\d,]+\.?\d*\)",  # (£1,234) or (1,234)
            r"£?\([\d,]+\.?\d*\)",  # £(1,234)
            r"\(([\d,]+)\)",        # Simple (1234)
        ],
        "currency_symbols": ["£", "GBP"],
        "scale_indicators": {
            "thousands": ["'000", "000s", "£'000", "£000"],
            "millions": ["m", "£m", "millions", "Million"],
            "actual": ["£", "GBP"]
        },
        "thousand_separator": ",",
        "decimal_point": "."
    },
    
    # Football-specific intangible assets accounting
    "player_registration_accounting": {
        "recognition": "intangible_assets",
        "measurement": "cost_less_amortisation",
        "common_terms": [
            "Players' registrations",
            "Player registrations",
            "Intangible assets",
            "Intangible fixed assets",
            "Player registration rights",
            "Amortisation of players' registrations",
            "Amortisation of intangible assets",
            "Profit/(loss) on disposal of players' registrations",
            "Profit on disposal of intangible assets",
            "Player trading"
        ],
        "amortisation_method": "straight_line_over_contract",
        "disposal_treatment": "gain_loss_not_revenue",
        "impairment_possible": True
    },
    
    # Expected sections with required and optional fields
    "expected_sections": {
        "profit_loss": {
            "common_names": [
                "Profit and Loss Account",
                "Statement of Comprehensive Income",
                "Income Statement",
                "Statement of Profit or Loss"
            ],
            "required_fields": [
                "turnover",
                "operating_profit",
                "profit_loss_before_tax"
            ],
            "optional_fields": [
                "cost_of_sales",
                "gross_profit",
                "administrative_expenses",
                "other_operating_income",
                "interest_receivable",
                "interest_payable",
                "tax_on_loss"
            ]
        },
        "balance_sheet": {
            "common_names": [
                "Balance Sheet",
                "Statement of Financial Position"
            ],
            "required_fields": [
                "total_assets",
                "net_assets",
                "cash_at_bank"
            ],
            "optional_fields": [
                "fixed_assets",
                "intangible_assets",
                "tangible_assets",
                "current_assets",
                "debtors",
                "creditors_due_within_one_year",
                "creditors_due_after_one_year",
                "net_current_liabilities",
                "total_assets_less_current_liabilities"
            ]
        },
        "turnover_note": {
            "common_names": [
                "Turnover and other revenue",
                "Revenue",
                "Turnover analysed by class of business",
                "Turnover analysed by geographical market"
            ],
            "fields": [
                "matchday_revenue",
                "broadcasting_revenue", 
                "commercial_revenue",
                "sponsorship_revenue",
                "retail_revenue",
                "other_revenue"
            ]
        }
    },
    
    # Revenue stream categories with aliases
    "revenue_categories": {
        "matchday": {
            "aliases": [
                "Matchday",
                "Matchday Admissions",
                "Gate receipts",
                "Ticket sales",
                "Matchday income",
                "Stadium Hire and Catering",
                "Hospitality"
            ],
            "typical_range_percentage": [5, 35]
        },
        "broadcasting": {
            "aliases": [
                "Broadcasting",
                "TV revenue",
                "Media revenue",
                "Broadcasting income",
                "Central distributions",
                "League distributions",
                "Broadcasting rights"
            ],
            "typical_range_percentage": [15, 75]
        },
        "commercial": {
            "aliases": [
                "Commercial",
                "Sponsorship and Advertising",
                "Sponsorship",
                "Retail",
                "Merchandising",
                "Other commercial",
                "Commercial revenue",
                "Sponsorship revenue"
            ],
            "typical_range_percentage": [15, 60]
        },
        "other": {
            "aliases": [
                "Other",
                "Other income",
                "Youth Department",
                "Stadium tours",
                "Conference and events"
            ],
            "typical_range_percentage": [0, 20]
        }
    },
    
    # Enhanced field mappings with contextual hints
    "field_mappings": {
        "turnover": {
            "primary_terms": ["Turnover", "Revenue", "Total revenue", "Total income"],
            "location_hints": ["first line of P&L", "top of income statement"],
            "validation": "should be positive"
        },
        "cash_at_bank": {
            "primary_terms": ["Cash at bank and in hand", "Cash and cash equivalents", "Cash"],
            "location_hints": ["current assets section", "bottom of current assets"],
            "validation": "usually positive, can be negative if overdrawn"
        },
        "operating_profit": {
            "primary_terms": ["Operating profit", "Operating loss", "Operating profit/(loss)"],
            "location_hints": ["after administrative expenses", "before interest"],
            "validation": "can be positive or negative"
        },
        "net_assets": {
            "primary_terms": ["Net assets", "Net liabilities", "Net assets/(liabilities)"],
            "location_hints": ["bottom of balance sheet", "after creditors due after one year"],
            "calculation": "total_assets - total_liabilities",
            "validation": "negative indicates net liabilities"
        },
        "creditors_due_after_one_year": {
            "primary_terms": [
                "Creditors: amounts falling due after more than one year",
                "Creditors due after one year",
                "Non-current liabilities"
            ],
            "location_hints": ["after net current liabilities", "before net assets"],
            "validation": "should be negative or shown in parentheses"
        },
        "player_wages": {
            "primary_terms": ["Wages and salaries", "Staff costs", "Player wages", "Employment costs"],
            "location_hints": ["in notes to accounts", "note on employees"],
            "validation": "should be positive, often largest expense"
        },
        "player_registrations": {
            "primary_terms": [
                "Intangible assets",
                "Players' registrations",
                "Player registrations",
                "Intangible fixed assets"
            ],
            "location_hints": ["fixed assets section", "top of balance sheet"],
            "validation": "should be positive unless fully amortised"
        }
    },
    
    # Validation rules and relationships
    "validation_rules": {
        "balance_sheet_equation": {
            "formula": "net_assets = total_assets - total_liabilities",
            "tolerance": 1000
        },
        "revenue_composition": {
            "formula": "turnover ≈ matchday + broadcasting + commercial + other",
            "tolerance_percentage": 5
        },
        "net_current_position": {
            "formula": "net_current_liabilities = current_assets - creditors_due_within_one_year",
            "tolerance": 1000
        },
        "required_relationships": [
            "turnover >= 0",
            "total_assets >= current_assets",
            "if net_assets < 0 then termed 'net liabilities'"
        ],
        "financial_health_metrics": {
            "wage_to_revenue_ratio": {
                "uefa_guideline": 0.70,
                "warning_threshold": 0.80,
                "critical_threshold": 1.00
            },
            "current_ratio": {
                "healthy": 1.0,
                "concerning": 0.5,
                "critical": 0.25
            }
        }
    },
    
    # Post-processing rules for common issues
    "post_processing_rules": [
        {
            "name": "convert_parentheses_to_negative",
            "description": "Convert UK accounting parentheses to negative numbers",
            "pattern": r"\(£?([\d,]+\.?\d*)\)",
            "action": "multiply_by_negative_one"
        },
        {
            "name": "validate_net_assets_calculation",
            "description": "Ensure net assets calculation is correct",
            "check": "abs(net_assets - (total_assets - total_liabilities)) < tolerance",
            "action": "recalculate_if_wrong"
        },
        {
            "name": "check_revenue_breakdown",
            "description": "Validate revenue components sum to turnover",
            "check": "abs(sum(revenue_components) - turnover) / turnover < 0.05",
            "action": "flag_for_review_if_false"
        },
        {
            "name": "fix_scale_errors",
            "description": "Detect and fix common scale errors (thousands vs millions)",
            "check": "if revenue < 100000 and contains '000s' indicator",
            "action": "multiply_by_1000"
        }
    ],
    
    # Extraction prompts with UK-specific context
    "extraction_prompts": {
        "system_prompt": """You are a UK chartered accountant specializing in football club financial statements.
        You understand FRS 102, UK GAAP, and Companies Act 2006 requirements.
        You know that in UK accounting, numbers in parentheses are negative.
        You understand football-specific accounting including player registrations as intangible assets.""",
        
        "balance_sheet_prompt": """Extract financial data from this UK Balance Sheet. Remember:
        - Numbers in parentheses like (£1,234) are NEGATIVE values
        - 'Net liabilities' means the company has negative net assets
        - 'Creditors: amounts falling due after more than one year' is a separate line item
        - 'Total assets less current liabilities' is a subtotal, not the final net assets
        - Player registrations appear as intangible assets
        - Look for both 'within one year' and 'after one year' creditor amounts""",
        
        "profit_loss_prompt": """Extract from this UK Profit and Loss Account. Note:
        - Operating loss shown as (£amount) is a negative number
        - Turnover breakdown (matchday, broadcasting, commercial) may be in the notes
        - Cost of sales includes player wages and amortisation of player registrations
        - Interest payable is an expense (negative)
        - Look for 'Loss for the financial year' if the company made a loss""",
        
        "notes_prompt": """Extract from the Notes to the Financial Statements:
        - Note 3 typically contains turnover breakdown by business class
        - Look for matchday, broadcasting, and commercial revenue splits
        - Staff costs note will contain wage information
        - Intangible assets note shows player registration values
        - Related party transactions show dealings with owners/directors"""
    },
    
    # Quality scoring for extraction confidence
    "quality_scoring": {
        "required_sections_weights": {
            "profit_loss": 0.25,
            "balance_sheet": 0.25,
            "cash_flow": 0.15,
            "notes": 0.20,
            "auditor_report": 0.15
        },
        "field_extraction_weights": {
            "turnover": 0.15,
            "net_assets": 0.15,
            "cash_at_bank": 0.10,
            "operating_profit": 0.10,
            "player_registrations": 0.05,
            "revenue_breakdown": 0.15,
            "creditors_within_one_year": 0.10,
            "creditors_after_one_year": 0.10,
            "profit_before_tax": 0.10
        },
        "confidence_thresholds": {
            "high": 0.80,
            "medium": 0.60,
            "low": 0.40
        }
    },
    
    # Common extraction errors and fixes
    "common_errors": {
        "negative_numbers": {
            "issue": "Parentheses not recognized as negative",
            "fix": "Apply parentheses-to-negative conversion",
            "example": "(13,109,908) should be -13109908"
        },
        "missing_creditors_after_year": {
            "issue": "Long-term creditors often missed",
            "fix": "Specifically search for 'Creditors: amounts falling due after more than one year'",
            "location": "Between 'Total assets less current liabilities' and 'Net assets'"
        },
        "revenue_categorization": {
            "issue": "Commercial vs Sponsorship confusion",
            "fix": "Sponsorship and Advertising usually maps to Commercial",
            "check": "Sum of categories should equal turnover"
        },
        "scale_confusion": {
            "issue": "Mixing thousands and actual amounts",
            "fix": "Check for '000 or £'000 indicators in headers",
            "validation": "Football club revenue typically £1M-£500M range"
        }
    }
}