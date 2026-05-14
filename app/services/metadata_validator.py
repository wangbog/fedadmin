"""
SAML Metadata Validator

Provides unified metadata validation including:
- XSD Schema validation
- Structure check (exactly one EntityDescriptor)
- SSO Descriptor check (IDPSSODescriptor/SPSSODescriptor)
- EntityID extraction and uniqueness check
- Scope validation (domain format)

Error codes:
E001: Uploaded file is empty
E002: Invalid XML format
E003: Metadata cannot contain EntitiesDescriptor
E004: Metadata root element must be EntityDescriptor
E005: Schema validation failed
E006: IdP metadata must contain IDPSSODescriptor
E007: SP metadata must contain SPSSODescriptor
E008: Metadata missing entityID attribute
E009: entityID must start with http://, https:// or urn:
E010: This entityID already exists (IdP)
E011: This entityID already exists (SP)
E012: IDPSSODescriptor must contain Extensions element
E013: Must contain shibmd:Scope element (covered by XSD)
E014: shibmd:Scope regexp attribute must be 'false'
E015: shibmd:Scope element cannot be empty
E016: Scope must be a valid domain format
"""

from dataclasses import dataclass, field
from typing import List, Optional
from lxml import etree
from werkzeug.datastructures import FileStorage
import xmlschema
import os
import re


@dataclass
class ValidationError:
    """Single validation error"""

    code: str  # Error code, e.g., 'E001'
    message: str  # User-friendly error message


@dataclass
class ValidationResult:
    """Validation result"""

    success: bool
    entity_id: Optional[str] = None
    scope: Optional[str] = None
    errors: List[ValidationError] = field(default_factory=list)

    def raise_if_error(self):
        """Raise exception if validation failed"""
        if not self.success:
            messages = [f"{e.code}: {e.message}" for e in self.errors]
            raise ValueError("; ".join(messages))


class MetadataValidator:
    """SAML Metadata validator"""

    NAMESPACES = {
        "md": "urn:oasis:names:tc:SAML:2.0:metadata",
        "shibmd": "urn:mace:shibboleth:metadata:1.0",
    }

    # XSD file base path
    XSD_DIR = os.path.join(os.path.dirname(__file__), "xsd")

    # Main XSD file path
    MAIN_XSD = os.path.join(XSD_DIR, "saml-schema-metadata-2.0.xsd")

    # Domain format regex (simplified)
    DOMAIN_REGEX = re.compile(
        r"^([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
    )

    @classmethod
    def validate(
        cls,
        entity_type: str,
        file_storage: FileStorage,
        exclude_id: Optional[int] = None,
    ) -> ValidationResult:
        """
        Validate uploaded metadata file.

        Args:
            entity_type: 'idp' or 'sp'
            file_storage: The uploaded file
            exclude_id: Entity ID to exclude (for edit mode to exclude self)

        Returns:
            ValidationResult containing validation results
        """
        result = ValidationResult(success=True)

        # 1. Read file content
        file_storage.seek(0)
        content = file_storage.read()
        file_storage.seek(0)

        if not content:
            result.success = False
            result.errors.append(ValidationError("E001", "Uploaded file is empty"))
            return result

        # 2. XML parsing check
        try:
            root = etree.fromstring(content)
        except etree.XMLSyntaxError as e:
            result.success = False
            result.errors.append(ValidationError("E002", f"Invalid XML format: {e}"))
            return result

        # 3. Structure check: must have exactly one EntityDescriptor, no EntitiesDescriptor
        cls._check_single_entity_descriptor(root, result)
        if not result.success:
            return result

        # 4. XSD Schema validation
        cls._validate_schema(content, result)
        if not result.success:
            return result

        # 5. SSO Descriptor check
        cls._check_sso_descriptor(entity_type, root, result)
        if not result.success:
            return result

        # 6. EntityID extraction and uniqueness check
        cls._validate_entity_id(root, entity_type, exclude_id, result)
        if not result.success:
            return result

        # 7. Scope validation (IdP only)
        if entity_type == "idp":
            cls._validate_scope(root, result)
            if not result.success:
                return result

        return result

    @staticmethod
    def _check_single_entity_descriptor(root, result):
        """Check: must have exactly one EntityDescriptor, no EntitiesDescriptor"""
        tag_local = etree.QName(root).localname

        # Cannot be EntitiesDescriptor
        if tag_local == "EntitiesDescriptor":
            result.success = False
            result.errors.append(
                ValidationError(
                    "E003",
                    "Metadata cannot contain EntitiesDescriptor, only single EntityDescriptor is allowed",
                )
            )
            return

        # Must be EntityDescriptor
        if tag_local != "EntityDescriptor":
            result.success = False
            result.errors.append(
                ValidationError(
                    "E004", "Metadata root element must be EntityDescriptor"
                )
            )

    @classmethod
    def _validate_schema(cls, content, result):
        """Validate schema using full XSD collection with proper import resolution"""
        try:
            # Load main XSD with absolute base path to correctly resolve all imports
            schema = xmlschema.XMLSchema(
                cls.MAIN_XSD, base_url=f"file://{os.path.abspath(cls.XSD_DIR)}/"
            )

            schema.validate(content)
        except xmlschema.XMLSchemaValidationError as e:
            result.success = False
            # Extract key error message
            error_msg = str(e).split("\n")[0] if "\n" in str(e) else str(e)
            result.errors.append(
                ValidationError("E005", f"Schema validation failed: {error_msg}")
            )

    @staticmethod
    def _check_sso_descriptor(entity_type, root, result):
        """Check SSO Descriptor existence (IDPSSODescriptor or SPSSODescriptor)"""
        ns = MetadataValidator.NAMESPACES

        if entity_type == "idp":
            descriptor = root.find(".//md:IDPSSODescriptor", ns)
            if descriptor is None:
                result.success = False
                result.errors.append(
                    ValidationError(
                        "E006", "IdP metadata must contain IDPSSODescriptor"
                    )
                )
        else:  # sp
            descriptor = root.find(".//md:SPSSODescriptor", ns)
            if descriptor is None:
                result.success = False
                result.errors.append(
                    ValidationError("E007", "SP metadata must contain SPSSODescriptor")
                )

    @staticmethod
    def _validate_entity_id(root, entity_type, exclude_id, result):
        """Extract and validate EntityID"""
        from app.models import Idp, Sp

        # Extract EntityID
        entity_id = root.get("entityID")
        if not entity_id:
            result.success = False
            result.errors.append(
                ValidationError("E008", "Metadata missing entityID attribute")
            )
            return

        # Basic format check
        if not (
            entity_id.startswith("http://")
            or entity_id.startswith("https://")
            or entity_id.startswith("urn:")
        ):
            result.success = False
            result.errors.append(
                ValidationError(
                    "E009", "entityID must start with http://, https:// or urn:"
                )
            )
            return

        result.entity_id = entity_id

        # Database uniqueness check
        if entity_type == "idp":
            existing = Idp.query.filter(Idp.idp_entityid == entity_id)
            if exclude_id:
                existing = existing.filter(Idp.idp_id != exclude_id)
            if existing.first():
                result.success = False
                result.errors.append(
                    ValidationError(
                        "E010", f"This entityID already exists: {entity_id}"
                    )
                )
        else:  # sp
            existing = Sp.query.filter(Sp.sp_entityid == entity_id)
            if exclude_id:
                existing = existing.filter(Sp.sp_id != exclude_id)
            if existing.first():
                result.success = False
                result.errors.append(
                    ValidationError(
                        "E011", f"This entityID already exists: {entity_id}"
                    )
                )

    @staticmethod
    def _validate_scope(root, result):
        """Extract and validate Scope (IdP only)"""
        ns = MetadataValidator.NAMESPACES

        # Find Scope
        idp_desc = root.find(".//md:IDPSSODescriptor", ns)
        if idp_desc is None:
            return

        extensions = idp_desc.find("md:Extensions", ns)
        if extensions is None:
            result.success = False
            result.errors.append(
                ValidationError(
                    "E012", "IDPSSODescriptor must contain Extensions element"
                )
            )
            return

        scope_elem = extensions.find("shibmd:Scope", ns)

        # Check regexp attribute
        regexp = scope_elem.get("regexp", "false").lower()
        if regexp != "false":
            result.success = False
            result.errors.append(
                ValidationError("E014", "shibmd:Scope regexp attribute must be 'false'")
            )
            return

        # Extract scope value
        scope = scope_elem.text
        if not scope or not scope.strip():
            result.success = False
            result.errors.append(
                ValidationError("E015", "shibmd:Scope element cannot be empty")
            )
            return

        scope = scope.strip()
        result.scope = scope

        # Domain format validation
        if not MetadataValidator.DOMAIN_REGEX.match(scope):
            result.success = False
            result.errors.append(
                ValidationError("E016", f"Scope must be a valid domain format: {scope}")
            )
