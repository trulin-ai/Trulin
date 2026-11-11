"""
Layer 3: Canonical Source Envelope Specification & Factory.
Standardizes every heterogeneous raw asset into an immutable, multi-tenant canonical container
with cryptographic integrity, precise locators, access scope, and provenance tracking.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Union

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.base import RawSourceAsset


class CanonicalSourceEnvelope(BaseModel):
    """
    Universal, immutable container sealing native assets with governance metadata.
    Preserves 100% of raw data structures without premature flattening.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    envelope_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for this envelope")
    organization_id: uuid.UUID = Field(..., description="Tenant organization boundary")
    source_id: uuid.UUID = Field(..., description="Parent DataSource identifier")
    asset_id: str = Field(..., description="Native external asset identifier (e.g., github://repo/path, mongodb://db/col/id)")
    
    # Layer 1 Governance Metadata
    source_family: SourceFamily = Field(..., description="Primary heterogeneous source family")
    source_intent: SourceIntent = Field(default=SourceIntent.GOVERNANCE_POLICY, description="Declared business intent")
    
    # Layer 2 Native Extraction Provenance
    native_format: str = Field(..., description="Native format descriptor (e.g., markdown, json, json_schema, sql_schema, pdf)")
    source_version: str = Field(..., description="Immutable version pointer (Git commit SHA, DB LSN, file version, timestamp)")
    content_hash: str = Field(..., description="Deterministic SHA-256 hash of the native payload")
    
    # Exact Evidence Locators
    locator_metadata: dict[str, Any] = Field(default_factory=dict, description="Contextual path coordinates (repo, branch, table, col)")
    evidence_locator: dict[str, Any] = Field(default_factory=dict, description="Fine-grained coordinates for quote & UI grounding")
    access_scope: dict[str, Any] = Field(default_factory=dict, description="Permission scopes and tenant boundaries")
    
    # Pristine Un-flattened Payload
    raw_payload: Union[str, dict[str, Any], list[Any], bytes] = Field(..., description="Un-flattened native data structure")
    
    # Metadata & State
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional connector and ingestion metadata")
    is_deleted: bool = Field(default=False, description="Tombstone flag for delta sync deletions")
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Capture timestamp in UTC")

    def get_payload_as_text(self) -> str:
        """Returns string representation of payload for inspection without mutating the original container."""
        if isinstance(self.raw_payload, str):
            return self.raw_payload
        if isinstance(self.raw_payload, bytes):
            return self.raw_payload.decode("utf-8", errors="replace")
        return json.dumps(self.raw_payload, default=str, indent=2)

    def to_dict(self) -> dict[str, Any]:
        """Serializes envelope to a dictionary with stringified enums and dates."""
        payload_data = self.raw_payload
        if isinstance(payload_data, bytes):
            payload_data = f"<binary: {len(payload_data)} bytes>"
            
        return {
            "envelope_id": str(self.envelope_id),
            "organization_id": str(self.organization_id),
            "source_id": str(self.source_id),
            "asset_id": self.asset_id,
            "source_family": self.source_family.value if hasattr(self.source_family, "value") else str(self.source_family),
            "source_intent": self.source_intent.value if hasattr(self.source_intent, "value") else str(self.source_intent),
            "native_format": self.native_format,
            "source_version": self.source_version,
            "content_hash": self.content_hash,
            "locator_metadata": self.locator_metadata,
            "evidence_locator": self.evidence_locator,
            "access_scope": self.access_scope,
            "raw_payload": payload_data,
            "metadata": self.metadata,
            "is_deleted": self.is_deleted,
            "captured_at": self.captured_at.isoformat(),
        }


class EnvelopeFactory:
    """Factory and validator for creating CanonicalSourceEnvelopes across all ingestion channels."""

    @staticmethod
    def calculate_hash(raw_payload: Union[str, dict[str, Any], list[Any], bytes]) -> str:
        """Computes deterministic SHA-256 hash across any payload type."""
        if isinstance(raw_payload, bytes):
            return hashlib.sha256(raw_payload).hexdigest()
        if isinstance(raw_payload, str):
            return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()
        serialized = json.dumps(raw_payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def create_from_raw_asset(
        cls,
        raw_asset: RawSourceAsset,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        source_intent: SourceIntent | None = None,
        access_scope: dict[str, Any] | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> CanonicalSourceEnvelope:
        """Wraps a Layer 2 RawSourceAsset into an immutable Layer 3 CanonicalSourceEnvelope."""
        # Calculate or verify hash
        content_hash = raw_asset.content_hash or cls.calculate_hash(raw_asset.raw_payload)
        
        # Merge metadata
        merged_meta = dict(raw_asset.metadata or {})
        if extra_metadata:
            merged_meta.update(extra_metadata)

        # Normalize source_family
        family = raw_asset.source_family
        if isinstance(family, str):
            try:
                family = SourceFamily(family)
            except ValueError:
                family = SourceFamily.DOCUMENT

        # Normalize source_intent
        intent = source_intent or SourceIntent.GOVERNANCE_POLICY
        if isinstance(intent, str):
            try:
                intent = SourceIntent(intent)
            except ValueError:
                intent = SourceIntent.GOVERNANCE_POLICY

        deterministic_seed = f"{organization_id}:{source_id}:{raw_asset.asset_id}:{content_hash}"
        envelope_id = uuid.uuid5(uuid.NAMESPACE_URL, deterministic_seed)

        return CanonicalSourceEnvelope(
            envelope_id=envelope_id,
            organization_id=organization_id,
            source_id=source_id,
            asset_id=raw_asset.asset_id,
            source_family=family,
            source_intent=intent,
            native_format=raw_asset.native_format or "unknown",
            source_version=raw_asset.source_version or "1",
            content_hash=content_hash,
            locator_metadata=raw_asset.locator_metadata or {},
            evidence_locator=raw_asset.evidence_locator or raw_asset.locator_metadata or {},
            access_scope=access_scope or {},
            raw_payload=raw_asset.raw_payload,
            metadata=merged_meta,
            is_deleted=raw_asset.is_deleted,
            captured_at=raw_asset.captured_at or datetime.now(timezone.utc),
        )

    @classmethod
    def create_from_file_upload(
        cls,
        filename: str,
        raw_bytes: bytes,
        parsed_content: str,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        document_type: str = "policy",
        source_intent: SourceIntent | None = None,
        access_scope: dict[str, Any] | None = None,
        source_family: SourceFamily | None = None,
    ) -> CanonicalSourceEnvelope:
        """Creates a canonical envelope for manual file uploads and connector-ingested documents."""
        content_hash = cls.calculate_hash(raw_bytes if raw_bytes else parsed_content)
        
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
        native_format_map = {
            "md": "markdown",
            "markdown": "markdown",
            "pdf": "pdf",
            "json": "json",
            "csv": "csv",
            "docx": "docx",
            "txt": "plain_text",
            "html": "html",
            "yaml": "yaml",
            "yml": "yaml",
            "png": "image",
            "jpg": "image",
            "jpeg": "image",
            "tiff": "image",
            "tif": "image",
            "webp": "image",
            "bmp": "image",
        }
        native_format = native_format_map.get(ext, ext)

        intent = source_intent or (
            SourceIntent.GOVERNANCE_POLICY if document_type == "policy" else SourceIntent.OPERATIONAL_DATA
        )

        resolved_family = source_family or (
            SourceFamily.DOCUMENT if native_format not in ("json", "csv") else SourceFamily.STRUCTURED
        )

        deterministic_seed = f"{organization_id}:{source_id}:file://{filename}:{content_hash}"
        envelope_id = uuid.uuid5(uuid.NAMESPACE_URL, deterministic_seed)

        return CanonicalSourceEnvelope(
            envelope_id=envelope_id,
            organization_id=organization_id,
            source_id=source_id,
            asset_id=f"file://{filename}",
            source_family=resolved_family,
            source_intent=intent,
            native_format=native_format,
            source_version="1",
            content_hash=content_hash,
            locator_metadata={
                "filename": filename,
                "file_extension": ext,
                "file_size": len(raw_bytes),
                "document_type": document_type,
            },
            evidence_locator={
                "filename": filename,
                "document_type": document_type,
            },
            access_scope=access_scope or {"upload_channel": "manual_file_upload"},
            raw_payload=parsed_content or raw_bytes,
            metadata={"filename": filename, "file_size": len(raw_bytes), "raw_bytes": raw_bytes},
            is_deleted=False,
            captured_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def validate_integrity(envelope: CanonicalSourceEnvelope) -> bool:
        """Validates that the envelope has not been tampered with or corrupted."""
        if not envelope.raw_payload and not envelope.is_deleted:
            return False
        expected_hash = EnvelopeFactory.calculate_hash(envelope.raw_payload)
        return envelope.content_hash == expected_hash
