"""
AI Classifier Component (Feature 4)
====================================

AI-powered document classification using Claude API.
- Extract text from PDFs
- Classify by visa criteria
- Return confidence scores
- Detect missing criteria
"""

import streamlit as st
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
import os
import io
import json
import re


@dataclass
class ClassificationResult:
    """Result of AI document classification"""
    document_id: str
    filename: str
    criterion_code: str  # e.g., 'O1A-1', 'P1A-7'
    criterion_name: str  # e.g., 'Awards and Prizes'
    document_type: str  # e.g., 'award_certificate', 'media_article'
    confidence_score: float  # 0.0-1.0
    reasoning: str
    suggested_exhibit_letter: str
    evidence_type: Optional[str] = None  # 'standard' or 'comparable' (not for P-1A)
    alternative_classifications: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'filename': self.filename,
            'criterion_code': self.criterion_code,
            'criterion_name': self.criterion_name,
            'document_type': self.document_type,
            'confidence_score': self.confidence_score,
            'reasoning': self.reasoning,
            'suggested_exhibit_letter': self.suggested_exhibit_letter,
            'evidence_type': self.evidence_type,
            'alternative_classifications': self.alternative_classifications
        }


# Visa criteria definitions
VISA_CRITERIA = {
    'O-1A': {
        'O1A-1': {'name': 'Awards & Prizes', 'keywords': ['award', 'prize', 'winner', 'recipient', 'honor', 'medal', 'trophy']},
        'O1A-2': {'name': 'Membership', 'keywords': ['member', 'association', 'organization', 'society', 'fellow', 'elected']},
        'O1A-3': {'name': 'Published Material', 'keywords': ['article', 'interview', 'media', 'publication', 'press', 'news', 'featured']},
        'O1A-4': {'name': 'Judging', 'keywords': ['judge', 'panel', 'evaluate', 'referee', 'review', 'jury', 'selection']},
        'O1A-5': {'name': 'Original Contributions', 'keywords': ['patent', 'invention', 'innovation', 'contribution', 'original', 'discovery']},
        'O1A-6': {'name': 'Scholarly Articles', 'keywords': ['journal', 'publication', 'research', 'paper', 'academic', 'peer-reviewed']},
        'O1A-7': {'name': 'Critical Role', 'keywords': ['employment', 'position', 'role', 'organization', 'lead', 'director', 'executive']},
        'O1A-8': {'name': 'High Salary', 'keywords': ['salary', 'compensation', 'pay', 'contract', 'remuneration', 'earnings']},
    },
    'O-1B': {
        'O1B-1': {'name': 'Lead/Starring Role', 'keywords': ['lead', 'star', 'principal', 'featured', 'headliner']},
        'O1B-2': {'name': 'Critical Reviews', 'keywords': ['review', 'critic', 'acclaim', 'praised', 'recognized']},
        'O1B-3': {'name': 'Major Commercial Success', 'keywords': ['box office', 'sales', 'revenue', 'commercial', 'success']},
        'O1B-4': {'name': 'High Salary', 'keywords': ['salary', 'compensation', 'pay', 'contract', 'fee']},
        'O1B-5': {'name': 'Recognition', 'keywords': ['award', 'nomination', 'honor', 'recognition']},
        'O1B-6': {'name': 'Distinguished Reputation', 'keywords': ['distinguished', 'renowned', 'prominent', 'reputation']},
    },
    'P-1A': {
        'P1A-1': {'name': 'Major U.S. League', 'keywords': ['league', 'team', 'contract', 'roster', 'professional']},
        'P1A-2': {'name': 'National Team', 'keywords': ['national', 'team', 'international', 'competition', 'country']},
        'P1A-3': {'name': 'Intercollegiate', 'keywords': ['college', 'ncaa', 'university', 'intercollegiate', 'collegiate']},
        'P1A-4': {'name': 'Federation Statement', 'keywords': ['federation', 'governing', 'official', 'statement', 'sanctioning']},
        'P1A-5': {'name': 'Expert Statement', 'keywords': ['expert', 'letter', 'recommendation', 'statement', 'opinion']},
        'P1A-6': {'name': 'International Ranking', 'keywords': ['ranking', 'ranked', 'position', 'standings', 'world']},
        'P1A-7': {'name': 'Honors & Awards', 'keywords': ['award', 'honor', 'champion', 'medal', 'title', 'trophy']},
    },
    'EB-1A': {
        'EB1A-1': {'name': 'Major Awards', 'keywords': ['award', 'prize', 'internationally', 'nationally', 'recognized']},
        'EB1A-2': {'name': 'Membership', 'keywords': ['member', 'association', 'outstanding', 'achievements']},
        'EB1A-3': {'name': 'Published Material', 'keywords': ['article', 'published', 'media', 'about', 'work']},
        'EB1A-4': {'name': 'Judging', 'keywords': ['judge', 'evaluate', 'panel', 'review']},
        'EB1A-5': {'name': 'Original Contributions', 'keywords': ['contribution', 'major', 'significance', 'field']},
        'EB1A-6': {'name': 'Scholarly Articles', 'keywords': ['scholarly', 'articles', 'professional', 'publications']},
        'EB1A-7': {'name': 'Artistic Exhibitions', 'keywords': ['exhibition', 'display', 'showcase', 'artistic']},
        'EB1A-8': {'name': 'Leading/Critical Role', 'keywords': ['leading', 'critical', 'role', 'organization']},
        'EB1A-9': {'name': 'High Salary', 'keywords': ['high', 'salary', 'remuneration', 'compensation']},
        'EB1A-10': {'name': 'Commercial Success', 'keywords': ['commercial', 'success', 'sales', 'box office']},
    }
}

# Document types
DOCUMENT_TYPES = {
    'award_certificate': ['certificate', 'award', 'diploma', 'recognition', 'trophy'],
    'media_article': ['article', 'news', 'interview', 'press', 'publication', 'magazine'],
    'expert_letter': ['letter', 'recommendation', 'attestation', 'statement', 'opinion'],
    'ranking_evidence': ['ranking', 'standings', 'position', 'leaderboard', 'list'],
    'contract': ['contract', 'agreement', 'employment', 'compensation', 'offer'],
    'passport': ['passport', 'travel', 'visa', 'immigration', 'i-94'],
    'form': ['form', 'i-129', 'i-907', 'g-1450', 'uscis', 'petition'],
    'competition_result': ['result', 'match', 'bout', 'competition', 'tournament', 'score'],
    'membership': ['membership', 'member', 'certificate', 'enrollment', 'card'],
    'salary_evidence': ['salary', 'pay', 'stub', 'w-2', 'tax', 'compensation'],
    'credential': ['degree', 'diploma', 'certificate', 'license', 'credential'],
    'brief': ['brief', 'petition', 'letter', 'support', 'cover'],
}


class AIClassifier:
    """AI-powered document classifier"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """Initialize classifier"""
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = model
        self.client = None

        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                st.warning("Anthropic package not installed. Using rule-based classification.")

    def extract_text_from_pdf(self, pdf_content: bytes, max_chars: int = 4000) -> str:
        """Extract text from PDF for classification"""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(pdf_content))
            text = ""
            for page in reader.pages[:5]:  # First 5 pages
                page_text = page.extract_text() or ""
                text += page_text + "\n"

            # If extracted text is empty or clearly a scanned placeholder, try OCR fallback
            cleaned = (text or "").strip()
            if (not cleaned) or len(cleaned) < 30 or 'adobe scan' in cleaned.lower():
                # Attempt OCR using pdf2image + pytesseract if available
                try:
                    from pdf2image import convert_from_bytes
                    import pytesseract
                    images = convert_from_bytes(pdf_content)
                    ocr_text_parts = []
                    for img in images[:10]:
                        try:
                            ocr_page = pytesseract.image_to_string(img)
                            ocr_text_parts.append(ocr_page)
                        except Exception:
                            continue
                    ocr_text = "\n\n".join(ocr_text_parts)
                    if ocr_text.strip():
                        return ocr_text[:max_chars]
                except Exception:
                    # OCR not available or failed; fall back to whatever we have
                    pass

            return text[:max_chars]
        except Exception as e:
            return f"[PDF text extraction failed: {e}]"

    def classify_document(
        self,
        pdf_content: bytes,
        filename: str,
        visa_type: str,
        document_id: str = ""
    ) -> ClassificationResult:
        """Classify a document"""
        extracted_text = self.extract_text_from_pdf(pdf_content)

        if self.client:
            return self._classify_with_ai(extracted_text, filename, visa_type, document_id)
        else:
            return self._classify_with_rules(extracted_text, filename, visa_type, document_id)

    def _classify_with_ai(
        self,
        text: str,
        filename: str,
        visa_type: str,
        document_id: str
    ) -> ClassificationResult:
        """Classify using Claude API"""
        criteria = VISA_CRITERIA.get(visa_type, VISA_CRITERIA['O-1A'])
        criteria_desc = "\n".join([f"- {code}: {info['name']}" for code, info in criteria.items()])

        prompt = f"""You are an expert immigration attorney assistant. Analyze this document for a {visa_type} visa petition.

DOCUMENT FILENAME: {filename}

EXTRACTED TEXT (first 4000 chars):
{text}

VISA TYPE: {visa_type}

AVAILABLE CRITERIA:
{criteria_desc}

Classify this document. Respond in this exact JSON format:
{{
    "criterion_code": "code like O1A-1 or P1A-7",
    "criterion_name": "full criterion name",
    "document_type": "one of: award_certificate, media_article, expert_letter, ranking_evidence, contract, passport, form, competition_result, membership, salary_evidence, credential, brief, other",
    "confidence_score": 0.0 to 1.0,
    "reasoning": "brief explanation",
    "suggested_exhibit_letter": "suggested letter like A, B, K",
    "evidence_type": {"null" if visa_type == 'P-1A' else '"standard" or "comparable"'},
    "alternative_classifications": [
        {{"criterion_code": "...", "confidence_score": 0.0-1.0}}
    ]
}}

IMPORTANT:
- P-1A has NO comparable evidence provision - evidence_type must be null
- Be specific about document type
- Provide reasoning"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text
            result = self._parse_json_response(result_text)

            return ClassificationResult(
                document_id=document_id,
                filename=filename,
                criterion_code=result.get('criterion_code', 'UNKNOWN'),
                criterion_name=result.get('criterion_name', 'Unknown'),
                document_type=result.get('document_type', 'other'),
                confidence_score=float(result.get('confidence_score', 0.5)),
                reasoning=result.get('reasoning', ''),
                suggested_exhibit_letter=result.get('suggested_exhibit_letter', 'Z'),
                evidence_type=result.get('evidence_type'),
                alternative_classifications=result.get('alternative_classifications', [])
            )
        except Exception as e:
            st.warning(f"AI classification failed: {e}. Using rule-based fallback.")
            return self._classify_with_rules(text, filename, visa_type, document_id)

    def generate_short_label(self, pdf_content: bytes, filename: str, visa_type: str = 'O-1A') -> str:
        """Generate a concise human-friendly label for a document using AI if available.

        Returns a short label (3-10 words). Falls back to heuristics if no AI client available.
        """
        text = self.extract_text_from_pdf(pdf_content, max_chars=2000)

        print(f'generate_short_label called for {filename}')

        # Try OpenAI if available
        try:
            import openai
            openai_api_key = os.getenv('OPENAI_API_KEY')
            print(f"OpenAI key present in env: {bool(openai_api_key)}")
            if openai_api_key:
                openai.api_key = openai_api_key
                prompt = (
                    f"Produce a very short (3-10 words) descriptive label for this immigration document."
                    f" Return only the label.\nFILENAME: {filename}\nTEXT:\n{text[:2000]}\nLABEL:"
                )
                print(f"Calling OpenAI for label: {filename}")
                resp = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=32,
                    temperature=0.0
                )
                label = resp['choices'][0]['message']['content'].strip().splitlines()[0]
                print(f"OpenAI label result: {label}")
                if label:
                    return label[:120]
        except Exception as e:
            print(f"OpenAI label attempt failed: {e}")

        # Try Anthropic if available
        if self.client:
            try:
                prompt = (
                    f"Produce a very short (3-10 words) descriptive label for this immigration document."
                    f" Return only the label.\nFILENAME: {filename}\nTEXT:\n{text[:2000]}\nLABEL:"
                )
                print(f"Calling Anthropic for label: {filename}")
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=60,
                    messages=[{"role": "user", "content": prompt}]
                )
                raw = response.content[0].text if hasattr(response, 'content') else str(response)
                label = raw.strip().splitlines()[0].strip(' "')
                print(f"Anthropic label result: {label}")
                if label:
                    return label[:120]
            except Exception:
                import traceback
                print(f"Anthropic label attempt failed: {traceback.format_exc()}")
                pass

        # Heuristic fallback
        lower = (text or "").lower() + " " + filename.lower()
        for key, kws in DOCUMENT_TYPES.items():
            if any(kw in lower for kw in kws):
                stem = os.path.splitext(filename)[0]
            label = f"{key.replace('_', ' ').title()} — {stem}"[:120]
            print(f"Heuristic label: {label}")
            return label

        # Use first meaningful line
        for line in (text or "").splitlines():
            s = line.strip()
            if len(s) > 20:
                print(f'First-line label: {s[:120]}')
            return s[:120]

        return os.path.splitext(filename)[0]

    def analyze_pdf(self, pdf_content: bytes, filename: str, visa_type: str = 'O-1A') -> Dict[str, Any]:
        """Return structured analysis of a PDF's content (summary, type, dates, forms, entities).

        Uses OpenAI/Anthropic when available; otherwise uses heuristics/regex.
        """
        text = self.extract_text_from_pdf(pdf_content, max_chars=8000)
        analysis: Dict[str, Any] = {
            'summary': None,
            'document_type': None,
            'dates': [],
            'forms': [],
            'visa_mentions': [],
            'entities': {},
        }

        # Try OpenAI for structured JSON
        try:
            import openai
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if openai_api_key:
                openai.api_key = openai_api_key
                prompt = (
                    "Extract a short JSON object with keys: summary (1-2 sentences), document_type, dates (array), forms (array), visa_mentions (array), entities (object)."
                    f"\nFILENAME: {filename}\nTEXT:\n{text[:4000]}\nJSON:"
                )
                resp = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=400,
                    temperature=0.0
                )
                result_text = resp['choices'][0]['message']['content']
                parsed = self._parse_json_response(result_text)
                if parsed:
                    for k in analysis.keys():
                        if k in parsed:
                            analysis[k] = parsed[k]
                    return analysis
        except Exception:
            pass

        # Try Anthropic
        if self.client:
            try:
                prompt = (
                    "Extract a short JSON object with keys: summary (1-2 sentences), document_type, dates (array), forms (array), visa_mentions (array), entities (object)."
                    f"\nFILENAME: {filename}\nTEXT:\n{text[:4000]}\nJSON:"
                )
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=400,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text
                parsed = self._parse_json_response(result_text)
                if parsed:
                    for k in analysis.keys():
                        if k in parsed:
                            analysis[k] = parsed[k]
                    return analysis
            except Exception:
                pass

        # Heuristic extraction
        import re

        # dates
        months = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        date_patterns = [r"\b\d{4}\b", r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", months + r" \d{1,2},? \d{4}"]
        found_dates = set()
        for p in date_patterns:
            for m in re.findall(p, text, flags=re.IGNORECASE):
                found_dates.add(m)
        analysis['dates'] = list(found_dates)

        # forms
        forms = set(m[1].upper() for m in re.findall(r"\b(Form\s+)?(I-129|I-907|G-1450|I-485|DS-160)\b", text, flags=re.IGNORECASE))
        analysis['forms'] = list(forms)

        # visa mentions
        visas = set(m.upper() for m in re.findall(r"\b(O-1A|O-1B|P-1A|P-1B|F-1|H-1B|EB-1A|EB-1B|EB-2)\b", text, flags=re.IGNORECASE))
        analysis['visa_mentions'] = list(visas)

        # document_type via keywords
        lower = (text or "").lower() + " " + filename.lower()
        for dtype, kws in DOCUMENT_TYPES.items():
            if any(kw in lower for kw in kws):
                analysis['document_type'] = dtype
                break

        # summary: first two meaningful lines
        summary_lines = []
        for line in (text or "").splitlines():
            s = line.strip()
            if len(s) > 30:
                summary_lines.append(s)
            if len(summary_lines) >= 2:
                break
        analysis['summary'] = ' '.join(summary_lines)[:500] if summary_lines else os.path.splitext(filename)[0]

        # simple entity extraction
        entities = {}
        for line in (text or "").splitlines():
            if 'student' in line.lower() or 'beneficiary' in line.lower() or 'petitioner' in line.lower():
                parts = line.split(':', 1)
                if len(parts) == 2:
                    entities[parts[0].strip()] = parts[1].strip()
        analysis['entities'] = entities

        return analysis

    def _classify_with_rules(
        self,
        text: str,
        filename: str,
        visa_type: str,
        document_id: str
    ) -> ClassificationResult:
        """Classify using keyword rules (fallback)"""
        text_lower = text.lower() + " " + filename.lower()
        criteria = VISA_CRITERIA.get(visa_type, VISA_CRITERIA['O-1A'])

        # Score each criterion
        scores = {}
        for code, info in criteria.items():
            score = sum(1 for kw in info['keywords'] if kw in text_lower)
            scores[code] = score

        # Get best match
        best_code = max(scores, key=scores.get) if scores else list(criteria.keys())[0]
        best_score = scores.get(best_code, 0)
        max_possible = len(criteria[best_code]['keywords'])
        confidence = min(best_score / max(max_possible, 1), 1.0) * 0.8  # Cap at 80% for rule-based

        # Detect document type
        doc_type = 'other'
        for dtype, keywords in DOCUMENT_TYPES.items():
            if any(kw in text_lower for kw in keywords):
                doc_type = dtype
                break

        # Suggest exhibit letter based on position
        letter_map = {i: chr(65 + i) for i in range(26)}
        criterion_index = list(criteria.keys()).index(best_code)
        suggested_letter = letter_map.get(criterion_index, 'Z')

        return ClassificationResult(
            document_id=document_id,
            filename=filename,
            criterion_code=best_code,
            criterion_name=criteria[best_code]['name'],
            document_type=doc_type,
            confidence_score=confidence,
            reasoning=f"Rule-based match on keywords: {', '.join(criteria[best_code]['keywords'][:3])}",
            suggested_exhibit_letter=suggested_letter,
            evidence_type=None if visa_type == 'P-1A' else 'standard',
            alternative_classifications=[]
        )

    def _parse_json_response(self, text: str) -> Dict:
        """Parse JSON from Claude response"""
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
        return {}

    def detect_missing_criteria(
        self,
        classifications: List[ClassificationResult],
        visa_type: str
    ) -> List[Dict[str, str]]:
        """Identify missing criteria for the visa type"""
        criteria = VISA_CRITERIA.get(visa_type, {})
        present_codes = {c.criterion_code for c in classifications}

        missing = []
        for code, info in criteria.items():
            if code not in present_codes:
                missing.append({
                    'criterion_code': code,
                    'criterion_name': info['name'],
                    'importance': 'recommended'
                })
        return missing

    def suggest_exhibit_order(
        self,
        classifications: List[ClassificationResult],
        visa_type: str
    ) -> List[ClassificationResult]:
        """Suggest optimal exhibit ordering"""
        criteria = VISA_CRITERIA.get(visa_type, {})
        criteria_order = list(criteria.keys())

        def sort_key(c: ClassificationResult) -> Tuple[int, float]:
            try:
                idx = criteria_order.index(c.criterion_code)
            except ValueError:
                idx = 999
            return (idx, -c.confidence_score)

        return sorted(classifications, key=sort_key)


def render_classification_ui(
    classifications: List[ClassificationResult],
    visa_type: str
) -> List[ClassificationResult]:
    """Render the classification results UI"""
    st.subheader("🤖 AI Classification Results")

    if not classifications:
        st.info("No documents classified yet. Upload files to begin.")
        return classifications

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        avg_confidence = sum(c.confidence_score for c in classifications) / len(classifications)
        st.metric("Average Confidence", f"{avg_confidence:.0%}")
    with col2:
        unique_criteria = len(set(c.criterion_code for c in classifications))
        st.metric("Criteria Covered", unique_criteria)
    with col3:
        st.metric("Documents", len(classifications))

    # Missing criteria warning
    classifier = AIClassifier()
    missing = classifier.detect_missing_criteria(classifications, visa_type)
    if missing:
        with st.expander(f"⚠️ Missing Criteria ({len(missing)})", expanded=True):
            for m in missing:
                st.write(f"- **{m['criterion_code']}**: {m['criterion_name']}")

    st.markdown("---")

    # Classification list
    updated_classifications = []
    for i, c in enumerate(classifications):
        with st.expander(
            f"📄 {c.filename} → **{c.criterion_name}** ({c.confidence_score:.0%})",
            expanded=False
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**Criterion**: {c.criterion_code} - {c.criterion_name}")
                st.write(f"**Document Type**: {c.document_type.replace('_', ' ').title()}")
                st.write(f"**Reasoning**: {c.reasoning}")
                if c.evidence_type:
                    st.write(f"**Evidence Type**: {c.evidence_type.title()}")

            with col2:
                # Allow override
                criteria = VISA_CRITERIA.get(visa_type, {})
                criterion_options = [f"{code}: {info['name']}" for code, info in criteria.items()]
                current_idx = next(
                    (i for i, opt in enumerate(criterion_options) if opt.startswith(c.criterion_code)),
                    0
                )

                new_criterion = st.selectbox(
                    "Override Classification",
                    options=criterion_options,
                    index=current_idx,
                    key=f"override_{i}"
                )

                # Parse override
                new_code = new_criterion.split(':')[0]
                if new_code != c.criterion_code:
                    c.criterion_code = new_code
                    c.criterion_name = criteria[new_code]['name']
                    c.reasoning = "Manually overridden"

            updated_classifications.append(c)

    return updated_classifications


def get_classifications() -> List[ClassificationResult]:
    """Get classifications from session state"""
    if 'classifications' not in st.session_state:
        st.session_state.classifications = []
    return [
        ClassificationResult(**c) if isinstance(c, dict) else c
        for c in st.session_state.classifications
    ]


def save_classifications(classifications: List[ClassificationResult]):
    """Save classifications to session state"""
    st.session_state.classifications = [c.to_dict() for c in classifications]
