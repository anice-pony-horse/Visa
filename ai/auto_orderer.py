"""
Auto Orderer - RAG-Based Exhibit Ordering
==========================================

Automatically orders exhibits based on:
1. Visa type standard ordering
2. RAG knowledge base recommendations
3. Best practices from successful petitions

Each visa type has a specific exhibit order that puts the
strongest evidence first.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Standard exhibit ordering by visa type
# Based on professional law firm best practices
EXHIBIT_ORDER = {
    "O-1A": {
        "sections": [
            {
                "name": "Administrative Documents",
                "exhibits": [
                    "Table of Contents",
                    "Form I-129 with O/P Supplement",
                    "Form G-28 (if applicable)",
                    "Form G-1450 (Credit Card Authorization)",
                    "Form I-907 (Premium Processing)",
                    "Filing Fee"
                ]
            },
            {
                "name": "Beneficiary Documents",
                "exhibits": [
                    "Passport (Biographical Pages)",
                    "Curriculum Vitae",
                    "Degree/Credentials"
                ]
            },
            {
                "name": "Petitioner Documents",
                "exhibits": [
                    "Petitioner Support Letter",
                    "Petitioner Evidence (registration, financials)",
                    "Employment Contract/Offer Letter"
                ]
            },
            {
                "name": "Criterion A - Awards",
                "criterion": "A",
                "exhibits": ["Award certificates", "Award significance documentation"]
            },
            {
                "name": "Criterion B - Membership",
                "criterion": "B",
                "exhibits": ["Membership documentation", "Association requirements"]
            },
            {
                "name": "Criterion C - Published Material",
                "criterion": "C",
                "exhibits": ["Media articles", "Publication credibility evidence"]
            },
            {
                "name": "Criterion D - Judging",
                "criterion": "D",
                "exhibits": ["Judging invitations", "Panel documentation"]
            },
            {
                "name": "Criterion E - Original Contributions",
                "criterion": "E",
                "exhibits": ["Contribution evidence", "Impact documentation"]
            },
            {
                "name": "Criterion F - Authorship",
                "criterion": "F",
                "exhibits": ["Scholarly articles", "Citation evidence"]
            },
            {
                "name": "Criterion G - Critical Employment",
                "criterion": "G",
                "exhibits": ["Employment evidence", "Organization reputation"]
            },
            {
                "name": "Criterion H - High Remuneration",
                "criterion": "H",
                "exhibits": ["Salary documentation", "Wage comparisons"]
            },
            {
                "name": "Supporting Documentation",
                "exhibits": ["Expert letters", "Additional evidence"]
            }
        ],
        "min_criteria": 3
    },
    "P-1A": {
        "sections": [
            {
                "name": "Administrative Documents",
                "exhibits": [
                    "Table of Contents",
                    "Form I-129 with O/P Supplement",
                    "Form G-28 (if applicable)",
                    "Form G-1450",
                    "Form I-907 (Premium Processing)",
                    "Consultation Letter from Labor Organization"
                ]
            },
            {
                "name": "Beneficiary Documents",
                "exhibits": [
                    "Passport (Biographical Pages)",
                    "Curriculum Vitae / Athletic Resume",
                    "Athletic Statistics/Records"
                ]
            },
            {
                "name": "Team/Event Documents",
                "exhibits": [
                    "Contract with Team/Event",
                    "Itinerary of Events",
                    "Team Roster"
                ]
            },
            {
                "name": "International Recognition Evidence",
                "criterion": "A",
                "exhibits": ["International event documentation", "League recognition"]
            },
            {
                "name": "Significant Achievements",
                "criterion": "B",
                "exhibits": ["Team achievements", "Championship records"]
            },
            {
                "name": "Awards Documentation",
                "criterion": "C",
                "exhibits": ["Sports awards", "MVP awards", "Records"]
            },
            {
                "name": "Ranking Evidence",
                "criterion": "D",
                "exhibits": ["Team rankings", "Individual rankings", "Statistics"]
            },
            {
                "name": "Media Coverage",
                "criterion": "E",
                "exhibits": ["Press coverage", "Sports media articles"]
            },
            {
                "name": "Supporting Documentation",
                "exhibits": ["Expert letters from coaches/scouts", "Additional evidence"]
            }
        ],
        "min_criteria": 2,
        "notes": "P-1A has NO comparable evidence provision. All evidence must directly satisfy criteria."
    },
    "EB-1A": {
        "sections": [
            {
                "name": "Administrative Documents",
                "exhibits": [
                    "Table of Contents",
                    "Form I-140",
                    "Form G-28 (if applicable)",
                    "Form I-485 (if concurrent filing)",
                    "Filing Fee"
                ]
            },
            {
                "name": "Beneficiary Documents",
                "exhibits": [
                    "Passport (Biographical Pages)",
                    "Birth Certificate",
                    "Curriculum Vitae",
                    "Degree/Credentials with Evaluation"
                ]
            },
            {
                "name": "Criterion A - Awards",
                "criterion": "A",
                "exhibits": ["Award documentation", "Award significance"]
            },
            {
                "name": "Criterion B - Membership",
                "criterion": "B",
                "exhibits": ["Membership documentation"]
            },
            {
                "name": "Criterion C - Published Material",
                "criterion": "C",
                "exhibits": ["Media articles about beneficiary"]
            },
            {
                "name": "Criterion D - Judging",
                "criterion": "D",
                "exhibits": ["Judging documentation"]
            },
            {
                "name": "Criterion E - Original Contributions",
                "criterion": "E",
                "exhibits": ["Contribution evidence", "Citations", "Impact"]
            },
            {
                "name": "Criterion F - Authorship",
                "criterion": "F",
                "exhibits": ["Scholarly publications", "Citation analysis"]
            },
            {
                "name": "Criterion H - Leading Role",
                "criterion": "H",
                "exhibits": ["Employment evidence", "Organization reputation"]
            },
            {
                "name": "Criterion I - High Salary",
                "criterion": "I",
                "exhibits": ["Salary documentation", "Wage surveys"]
            },
            {
                "name": "Supporting Documentation",
                "exhibits": ["Expert letters", "Additional evidence"]
            }
        ],
        "min_criteria": 3,
        "notes": "EB-1A requires satisfaction of 3+ criteria AND final merits determination (Kazarian analysis)"
    },
    "O-1B": {
        "sections": [
            {
                "name": "Administrative Documents",
                "exhibits": ["Table of Contents", "Form I-129", "Forms", "Fees"]
            },
            {
                "name": "Beneficiary Documents",
                "exhibits": ["Passport", "CV", "Credits/Filmography"]
            },
            {
                "name": "Criterion A - Lead/Starring Role",
                "criterion": "A",
                "exhibits": ["Lead role evidence", "Production credits"]
            },
            {
                "name": "Criterion B - Critical Reviews",
                "criterion": "B",
                "exhibits": ["Reviews", "Press coverage"]
            },
            {
                "name": "Criterion C - Distinguished Reputation",
                "criterion": "C",
                "exhibits": ["Organization reputation", "Lead role evidence"]
            },
            {
                "name": "Criterion D - Commercial Success",
                "criterion": "D",
                "exhibits": ["Box office", "Ratings", "Sales"]
            },
            {
                "name": "Criterion E - Significant Recognition",
                "criterion": "E",
                "exhibits": ["Recognition from experts", "Industry awards"]
            },
            {
                "name": "Criterion F - High Remuneration",
                "criterion": "F",
                "exhibits": ["Salary documentation"]
            },
            {
                "name": "Supporting Documentation",
                "exhibits": ["Expert letters", "Additional evidence"]
            }
        ],
        "min_criteria": 3
    }
}


@dataclass
class OrderedExhibit:
    """Exhibit with ordering information"""
    id: str
    filename: str
    category: str
    criterion: str
    criterion_letter: str
    section_index: int
    within_section_index: int
    exhibit_number: str


class AutoOrderer:
    """
    Automatically orders exhibits based on visa type and best practices.
    """

    def __init__(self, visa_type: str):
        """
        Initialize orderer for specific visa type.

        Args:
            visa_type: Visa type (O-1A, P-1A, EB-1A, etc.)
        """
        self.visa_type = visa_type
        self.order_config = EXHIBIT_ORDER.get(visa_type, EXHIBIT_ORDER["O-1A"])

    def order_exhibits(
        self,
        exhibits: List[Dict[str, Any]],
        numbering_style: str = "letters"
    ) -> List[OrderedExhibit]:
        """
        Order exhibits according to visa type standards.

        Args:
            exhibits: List of exhibit dicts with 'filename', 'category', 'criterion_letter'
            numbering_style: 'letters', 'numbers', or 'roman'

        Returns:
            List of OrderedExhibit in proper order
        """
        ordered = []
        sections = self.order_config["sections"]

        # Group exhibits by section
        section_map = {i: [] for i in range(len(sections))}
        unmatched = []

        for exhibit in exhibits:
            placed = False
            criterion = exhibit.get("criterion_letter", "")
            category = exhibit.get("category", "").lower()

            # Try to match to a section
            for i, section in enumerate(sections):
                section_criterion = section.get("criterion", "")
                section_name = section["name"].lower()

                # Match by criterion letter
                if criterion and criterion == section_criterion:
                    section_map[i].append(exhibit)
                    placed = True
                    break

                # Match by category/name
                if any(cat.lower() in category or category in cat.lower()
                       for cat in [section_name] + section.get("exhibits", [])):
                    section_map[i].append(exhibit)
                    placed = True
                    break

            if not placed:
                unmatched.append(exhibit)

        # Build ordered list
        exhibit_num = 0
        for section_idx, section_exhibits in section_map.items():
            for within_idx, exhibit in enumerate(section_exhibits):
                number = self._get_exhibit_number(exhibit_num, numbering_style)

                ordered.append(OrderedExhibit(
                    id=exhibit.get("id", str(exhibit_num)),
                    filename=exhibit.get("filename", ""),
                    category=exhibit.get("category", ""),
                    criterion=exhibit.get("criterion", ""),
                    criterion_letter=exhibit.get("criterion_letter", ""),
                    section_index=section_idx,
                    within_section_index=within_idx,
                    exhibit_number=number
                ))
                exhibit_num += 1

        # Add unmatched at end
        for exhibit in unmatched:
            number = self._get_exhibit_number(exhibit_num, numbering_style)
            ordered.append(OrderedExhibit(
                id=exhibit.get("id", str(exhibit_num)),
                filename=exhibit.get("filename", ""),
                category=exhibit.get("category", "Other"),
                criterion=exhibit.get("criterion", ""),
                criterion_letter=exhibit.get("criterion_letter", ""),
                section_index=len(sections),
                within_section_index=len(unmatched) - 1,
                exhibit_number=number
            ))
            exhibit_num += 1

        return ordered

    def _get_exhibit_number(self, index: int, style: str) -> str:
        """Generate exhibit number based on style."""
        if style == "letters":
            if index < 26:
                return chr(65 + index)
            else:
                # AA, AB, etc.
                first = chr(65 + (index // 26) - 1)
                second = chr(65 + (index % 26))
                return first + second
        elif style == "numbers":
            return str(index + 1)
        elif style == "roman":
            return self._to_roman(index + 1)
        return chr(65 + index)

    def _to_roman(self, num: int) -> str:
        """Convert number to Roman numeral."""
        val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']
        roman = ''
        for i, v in enumerate(val):
            while num >= v:
                roman += syms[i]
                num -= v
        return roman

    def get_section_names(self) -> List[str]:
        """Get list of section names for this visa type."""
        return [s["name"] for s in self.order_config["sections"]]

    def get_criteria_claimed(self, exhibits: List[Dict]) -> List[str]:
        """Get list of criteria letters claimed by exhibits."""
        criteria = set()
        for exhibit in exhibits:
            letter = exhibit.get("criterion_letter", "")
            if letter and letter != "N/A":
                criteria.add(letter)
        return sorted(list(criteria))

    def validate_criteria_count(self, exhibits: List[Dict]) -> Dict[str, Any]:
        """
        Validate that enough criteria are claimed.

        Returns:
            Dict with 'valid', 'claimed', 'required', 'message'
        """
        claimed = self.get_criteria_claimed(exhibits)
        required = self.order_config.get("min_criteria", 3)

        return {
            "valid": len(claimed) >= required,
            "claimed": len(claimed),
            "required": required,
            "criteria": claimed,
            "message": f"Claiming {len(claimed)} of {required} required criteria"
        }


def get_criterion_order(visa_type: str) -> List[str]:
    """
    Get the standard criterion order for a visa type.

    Args:
        visa_type: Visa type

    Returns:
        List of criterion letters in recommended order
    """
    config = EXHIBIT_ORDER.get(visa_type, EXHIBIT_ORDER["O-1A"])
    criteria = []
    for section in config["sections"]:
        if "criterion" in section:
            criteria.append(section["criterion"])
    return criteria


def auto_order_exhibits(
    exhibits: List[Dict[str, Any]],
    visa_type: str,
    numbering_style: str = "letters"
) -> List[Dict[str, Any]]:
    """
    Convenience function to auto-order exhibits.

    Args:
        exhibits: List of exhibit dicts
        visa_type: Visa type
        numbering_style: Numbering style

    Returns:
        List of ordered exhibits with numbers assigned
    """
    orderer = AutoOrderer(visa_type)
    ordered = orderer.order_exhibits(exhibits, numbering_style)

    # Convert back to dicts
    result = []
    for item in ordered:
        result.append({
            "id": item.id,
            "filename": item.filename,
            "category": item.category,
            "criterion": item.criterion,
            "criterion_letter": item.criterion_letter,
            "exhibit_number": item.exhibit_number,
            "section_index": item.section_index
        })

    return result
