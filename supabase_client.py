"""
Supabase Client
===============

Database operations for Visa Exhibit Generator V2.0.
Handles cases, exhibits, packages, and user data.

Tables:
- users: User profiles and preferences
- visa_cases: Case tracking with AI analysis
- exhibit_packages: Generated packages with stats
- exhibits: Individual exhibit records
- ai_classifications: AI decision audit trail
- generation_history: Action logging
- compression_stats: Performance metrics
- exhibit_templates: Reusable structures
"""

import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import json

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

from config import get_config


@dataclass
class VisaCase:
    """Visa case record"""
    id: Optional[str] = None
    user_id: Optional[str] = None
    visa_category: Optional[str] = None
    beneficiary_name: Optional[str] = None
    petitioner_name: Optional[str] = None
    petition_structure: Optional[str] = None
    processing_type: Optional[str] = None
    status: str = "draft"  # draft, processing, completed, archived
    ai_analysis: Optional[Dict] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'visa_category': self.visa_category,
            'beneficiary_name': self.beneficiary_name,
            'petitioner_name': self.petitioner_name,
            'petition_structure': self.petition_structure,
            'processing_type': self.processing_type,
            'status': self.status,
            'ai_analysis': self.ai_analysis,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VisaCase':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ExhibitPackage:
    """Exhibit package record"""
    id: Optional[str] = None
    case_id: Optional[str] = None
    user_id: Optional[str] = None
    exhibit_count: int = 0
    total_pages: int = 0
    original_size: int = 0
    compressed_size: int = 0
    compression_method: Optional[str] = None
    file_path: Optional[str] = None
    storage_url: Optional[str] = None
    shareable_link_id: Optional[str] = None
    expires_at: Optional[str] = None
    download_count: int = 0
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'case_id': self.case_id,
            'user_id': self.user_id,
            'exhibit_count': self.exhibit_count,
            'total_pages': self.total_pages,
            'original_size': self.original_size,
            'compressed_size': self.compressed_size,
            'compression_method': self.compression_method,
            'file_path': self.file_path,
            'storage_url': self.storage_url,
            'shareable_link_id': self.shareable_link_id,
            'expires_at': self.expires_at,
            'download_count': self.download_count,
            'created_at': self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExhibitPackage':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Exhibit:
    """Individual exhibit record"""
    id: Optional[str] = None
    package_id: Optional[str] = None
    case_id: Optional[str] = None
    exhibit_number: str = ""
    exhibit_name: str = ""
    filename: str = ""
    category: Optional[str] = None
    criterion_code: Optional[str] = None
    confidence_score: float = 0.0
    page_count: int = 0
    file_size: int = 0
    compressed_size: int = 0
    ai_reasoning: Optional[str] = None
    user_override: bool = False
    order: int = 0
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'package_id': self.package_id,
            'case_id': self.case_id,
            'exhibit_number': self.exhibit_number,
            'exhibit_name': self.exhibit_name,
            'filename': self.filename,
            'category': self.category,
            'criterion_code': self.criterion_code,
            'confidence_score': self.confidence_score,
            'page_count': self.page_count,
            'file_size': self.file_size,
            'compressed_size': self.compressed_size,
            'ai_reasoning': self.ai_reasoning,
            'user_override': self.user_override,
            'order': self.order,
            'created_at': self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Exhibit':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class SupabaseClient:
    """Supabase database client"""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """Initialize Supabase client"""
        self.client: Optional[Client] = None

        if not SUPABASE_AVAILABLE:
            return

        config = get_config()
        self.url = url or config.supabase_url
        self.key = key or config.supabase_key

        if self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
            except Exception as e:
                print(f"Failed to initialize Supabase: {e}")
                self.client = None

    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.client is not None

    # ==================== CASES ====================

    def create_case(self, case: VisaCase) -> Optional[VisaCase]:
        """Create a new visa case"""
        if not self.client:
            return None

        try:
            data = case.to_dict()
            data.pop('id', None)  # Remove id for insert
            data.pop('created_at', None)
            data.pop('updated_at', None)

            result = self.client.table('visa_cases').insert(data).execute()
            if result.data:
                return VisaCase.from_dict(result.data[0])
        except Exception as e:
            print(f"Error creating case: {e}")
        return None

    def get_case(self, case_id: str) -> Optional[VisaCase]:
        """Get case by ID"""
        if not self.client:
            return None

        try:
            result = self.client.table('visa_cases').select('*').eq('id', case_id).execute()
            if result.data:
                return VisaCase.from_dict(result.data[0])
        except Exception as e:
            print(f"Error getting case: {e}")
        return None

    def get_user_cases(self, user_id: str, limit: int = 50) -> List[VisaCase]:
        """Get cases for a user"""
        if not self.client:
            return []

        try:
            result = (
                self.client.table('visa_cases')
                .select('*')
                .eq('user_id', user_id)
                .order('created_at', desc=True)
                .limit(limit)
                .execute()
            )
            return [VisaCase.from_dict(r) for r in result.data]
        except Exception as e:
            print(f"Error getting user cases: {e}")
        return []

    def update_case(self, case_id: str, updates: Dict[str, Any]) -> Optional[VisaCase]:
        """Update a case"""
        if not self.client:
            return None

        try:
            updates['updated_at'] = datetime.now().isoformat()
            result = (
                self.client.table('visa_cases')
                .update(updates)
                .eq('id', case_id)
                .execute()
            )
            if result.data:
                return VisaCase.from_dict(result.data[0])
        except Exception as e:
            print(f"Error updating case: {e}")
        return None

    def delete_case(self, case_id: str) -> bool:
        """Delete a case"""
        if not self.client:
            return False

        try:
            self.client.table('visa_cases').delete().eq('id', case_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting case: {e}")
        return False

    # ==================== PACKAGES ====================

    def create_package(self, package: ExhibitPackage) -> Optional[ExhibitPackage]:
        """Create a new exhibit package"""
        if not self.client:
            return None

        try:
            data = package.to_dict()
            data.pop('id', None)
            data.pop('created_at', None)

            result = self.client.table('exhibit_packages').insert(data).execute()
            if result.data:
                return ExhibitPackage.from_dict(result.data[0])
        except Exception as e:
            print(f"Error creating package: {e}")
        return None

    def get_package(self, package_id: str) -> Optional[ExhibitPackage]:
        """Get package by ID"""
        if not self.client:
            return None

        try:
            result = self.client.table('exhibit_packages').select('*').eq('id', package_id).execute()
            if result.data:
                return ExhibitPackage.from_dict(result.data[0])
        except Exception as e:
            print(f"Error getting package: {e}")
        return None

    def get_case_packages(self, case_id: str) -> List[ExhibitPackage]:
        """Get packages for a case"""
        if not self.client:
            return []

        try:
            result = (
                self.client.table('exhibit_packages')
                .select('*')
                .eq('case_id', case_id)
                .order('created_at', desc=True)
                .execute()
            )
            return [ExhibitPackage.from_dict(r) for r in result.data]
        except Exception as e:
            print(f"Error getting case packages: {e}")
        return []

    def update_package(self, package_id: str, updates: Dict[str, Any]) -> Optional[ExhibitPackage]:
        """Update a package"""
        if not self.client:
            return None

        try:
            result = (
                self.client.table('exhibit_packages')
                .update(updates)
                .eq('id', package_id)
                .execute()
            )
            if result.data:
                return ExhibitPackage.from_dict(result.data[0])
        except Exception as e:
            print(f"Error updating package: {e}")
        return None

    def increment_download_count(self, package_id: str) -> bool:
        """Increment package download count"""
        if not self.client:
            return False

        try:
            # Get current count
            package = self.get_package(package_id)
            if package:
                self.update_package(package_id, {'download_count': package.download_count + 1})
                return True
        except Exception as e:
            print(f"Error incrementing download count: {e}")
        return False

    # ==================== EXHIBITS ====================

    def create_exhibit(self, exhibit: Exhibit) -> Optional[Exhibit]:
        """Create a new exhibit"""
        if not self.client:
            return None

        try:
            data = exhibit.to_dict()
            data.pop('id', None)
            data.pop('created_at', None)

            result = self.client.table('exhibits').insert(data).execute()
            if result.data:
                return Exhibit.from_dict(result.data[0])
        except Exception as e:
            print(f"Error creating exhibit: {e}")
        return None

    def create_exhibits_batch(self, exhibits: List[Exhibit]) -> List[Exhibit]:
        """Create multiple exhibits at once"""
        if not self.client:
            return []

        try:
            data = []
            for exhibit in exhibits:
                d = exhibit.to_dict()
                d.pop('id', None)
                d.pop('created_at', None)
                data.append(d)

            result = self.client.table('exhibits').insert(data).execute()
            return [Exhibit.from_dict(r) for r in result.data]
        except Exception as e:
            print(f"Error creating exhibits batch: {e}")
        return []

    def get_package_exhibits(self, package_id: str) -> List[Exhibit]:
        """Get exhibits for a package"""
        if not self.client:
            return []

        try:
            result = (
                self.client.table('exhibits')
                .select('*')
                .eq('package_id', package_id)
                .order('order')
                .execute()
            )
            return [Exhibit.from_dict(r) for r in result.data]
        except Exception as e:
            print(f"Error getting package exhibits: {e}")
        return []

    def update_exhibit(self, exhibit_id: str, updates: Dict[str, Any]) -> Optional[Exhibit]:
        """Update an exhibit"""
        if not self.client:
            return None

        try:
            result = (
                self.client.table('exhibits')
                .update(updates)
                .eq('id', exhibit_id)
                .execute()
            )
            if result.data:
                return Exhibit.from_dict(result.data[0])
        except Exception as e:
            print(f"Error updating exhibit: {e}")
        return None

    # ==================== AI CLASSIFICATIONS ====================

    def log_classification(
        self,
        exhibit_id: str,
        case_id: str,
        visa_type: str,
        criterion_code: str,
        confidence_score: float,
        reasoning: str,
        model_version: str = "claude-3"
    ) -> bool:
        """Log an AI classification for audit"""
        if not self.client:
            return False

        try:
            data = {
                'exhibit_id': exhibit_id,
                'case_id': case_id,
                'visa_type': visa_type,
                'criterion_code': criterion_code,
                'confidence_score': confidence_score,
                'reasoning': reasoning,
                'model_version': model_version,
            }
            self.client.table('ai_classifications').insert(data).execute()
            return True
        except Exception as e:
            print(f"Error logging classification: {e}")
        return False

    # ==================== GENERATION HISTORY ====================

    def log_generation(
        self,
        case_id: str,
        user_id: str,
        action: str,
        details: Optional[Dict] = None
    ) -> bool:
        """Log a generation action"""
        if not self.client:
            return False

        try:
            data = {
                'case_id': case_id,
                'user_id': user_id,
                'action': action,
                'details': details or {},
            }
            self.client.table('generation_history').insert(data).execute()
            return True
        except Exception as e:
            print(f"Error logging generation: {e}")
        return False

    # ==================== COMPRESSION STATS ====================

    def log_compression(
        self,
        package_id: str,
        original_size: int,
        compressed_size: int,
        method: str,
        quality_preset: str,
        duration_ms: int
    ) -> bool:
        """Log compression statistics"""
        if not self.client:
            return False

        try:
            reduction_percent = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            data = {
                'package_id': package_id,
                'original_size': original_size,
                'compressed_size': compressed_size,
                'reduction_percent': reduction_percent,
                'method': method,
                'quality_preset': quality_preset,
                'duration_ms': duration_ms,
            }
            self.client.table('compression_stats').insert(data).execute()
            return True
        except Exception as e:
            print(f"Error logging compression: {e}")
        return False

    # ==================== STORAGE ====================

    def upload_package(self, package_id: str, file_path: str) -> Optional[str]:
        """Upload package PDF to storage"""
        if not self.client:
            return None

        try:
            import os
            filename = f"{package_id}/{os.path.basename(file_path)}"

            with open(file_path, 'rb') as f:
                result = self.client.storage.from_('exhibit-packages').upload(
                    filename,
                    f,
                    {"content-type": "application/pdf"}
                )

            # Get public URL
            url = self.client.storage.from_('exhibit-packages').get_public_url(filename)
            return url

        except Exception as e:
            print(f"Error uploading package: {e}")
        return None

    def get_package_download_url(self, package_id: str, filename: str, expires_in: int = 3600) -> Optional[str]:
        """Get signed download URL for package"""
        if not self.client:
            return None

        try:
            path = f"{package_id}/{filename}"
            result = self.client.storage.from_('exhibit-packages').create_signed_url(
                path,
                expires_in
            )
            return result.get('signedURL')
        except Exception as e:
            print(f"Error getting download URL: {e}")
        return None


# Global client instance
_client: Optional[SupabaseClient] = None


def get_supabase() -> SupabaseClient:
    """Get global Supabase client instance"""
    global _client
    if _client is None:
        _client = SupabaseClient()
    return _client


def init_supabase(url: str, key: str) -> SupabaseClient:
    """Initialize Supabase with custom credentials"""
    global _client
    _client = SupabaseClient(url, key)
    return _client
