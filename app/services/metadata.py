import os
import logging
import tempfile
import subprocess
import portalocker
import yaml
import uuid
import hashlib
import json
import shutil
from datetime import datetime, timedelta
from lxml import etree
from flask import current_app, flash
from app.models import Federation, Organization, Idp, Sp
from app.models.edugain_status import EdugainStatus
from app.models.entity_status import EntityStatus
from app.services.metadata_validator import MetadataValidator
from app.utils.http_helpers import fetch_url
from app.extensions import db

logger = logging.getLogger(__name__)


class MetadataService:
    """SAML federation metadata processing service (using pyFF command-line tool)."""

    # Standard namespace definitions
    NAMESPACES = {
        "md": "urn:oasis:names:tc:SAML:2.0:metadata",
        "mdrpi": "urn:oasis:names:tc:SAML:metadata:rpi",
        "mdui": "urn:oasis:names:tc:SAML:metadata:ui",
        "shibmd": "urn:mace:shibboleth:metadata:1.0",
        "mdattr": "urn:oasis:names:tc:SAML:metadata:attribute",
        "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
        "remd": "http://refeds.org/metadata",
    }

    def __init__(self, app=None):
        self.app = app

    # ==========================
    # Public Static Methods
    # ==========================

    @classmethod
    def safe_regenerate(
        cls, app=None, output_path_key=None, statuses=None, edugain_only=False
    ):
        """Safely regenerate federation metadata.
        - output_path_key: config key for output path (e.g., 'FEDERATION_METADATA_OUTPUT')
        - statuses: list of status values to include (None means all)
        - edugain_only: if True, only include entities with eduGAIN enabled
        """
        if app is None:
            app = current_app._get_current_object()
        try:
            service = cls(app)
            service._regenerate(
                output_path_key, statuses=statuses, edugain_only=edugain_only
            )
            logger.info(
                f"[Metadata] Regeneration completed successfully: {output_path_key}"
            )
        except Exception as e:
            logger.exception(f"[Metadata] Regeneration failed: {output_path_key} - {e}")

    @classmethod
    def safe_retransform_all(cls, app=None):
        """
        Safely re-transform all entities metadata.
        Executes synchronously, intended to be called from background tasks.
        """
        if app is None:
            app = current_app._get_current_object()
        try:
            service = cls(app)
            service._retransform_all_entities()
            logger.info(
                "[Metadata] Full re-transformation and regeneration completed successfully."
            )
        except Exception as e:
            logger.exception(
                f"[Metadata] Full re-transformation and regeneration failed: {e}"
            )

    @classmethod
    def safe_transform(
        cls, entity_type, entity_id, original_path, organization_id, app=None
    ):
        """
        Safely transform entity metadata, catching exceptions and showing flash messages.
        """
        if app is None:
            app = current_app._get_current_object()
        try:
            service = cls(app)
            service._transform_entity(
                entity_type, entity_id, original_path, organization_id
            )
            logger.info(
                f"[Metadata] Transformation completed successfully: {entity_type} #{entity_id}"
            )
        except Exception as e:
            flash(f"Failed to transform metadata: {e}", "error")
            logger.exception(
                f"[Metadata] Transformation failed: {entity_type} #{entity_id} - {e}"
            )

    @staticmethod
    def validate_metadata(entity_type, file_storage, exclude_id=None):
        """Validate metadata file using MetadataValidator.

        Args:
            entity_type: 'idp' or 'sp'
            file_storage: The uploaded file
            exclude_id: Exclude entity ID for uniqueness check (for edit mode)

        Returns:
            ValidationResult with entity_id and scope
        """
        return MetadataValidator.validate(entity_type, file_storage, exclude_id)

    @staticmethod
    def fetch_edugain_metadata(entity_id):
        """
        Fetch already transformed metadata from eduGAIN API

        Args:
            entity_id: SAML entity ID

        Returns:
            (success status, metadata XML content or error message)
        """
        api_url = (
            f"https://technical.edugain.org/api?action=show_entity&e_id={entity_id}"
        )

        logger.info(f"[Metadata] Fetching metadata from eduGAIN: {entity_id}")

        success, content = fetch_url(api_url)

        if not success:
            return False, content

        # Validate returned content is valid XML
        try:
            etree.fromstring(content.encode("utf-8"))
        except etree.XMLSyntaxError as e:
            error_msg = f"eduGAIN returned invalid XML: {str(e)}"
            logger.error(f"[Metadata] {error_msg}")
            return False, error_msg

        logger.info(
            f"[Metadata] Successfully fetched metadata from eduGAIN: {entity_id}"
        )
        return True, content

    @staticmethod
    def calculate_sha1(content):
        """Calculate SHA1 hash of content"""
        return hashlib.sha1(content.encode("utf-8")).hexdigest()

    @staticmethod
    def extract_scope_from_idp_metadata(metadata_content):
        """
        Extract shibmd:Scope value from IdP metadata XML

        Args:
            metadata_content: XML string of metadata

        Returns:
            Scope string if found, None otherwise
        """
        try:
            root = etree.fromstring(metadata_content.encode("utf-8"))
            ns = {
                "md": MetadataService.NAMESPACES["md"],
                "shibmd": MetadataService.NAMESPACES["shibmd"],
            }
            scope_elem = root.find(".//shibmd:Scope", namespaces=ns)
            if scope_elem is not None and scope_elem.text:
                return scope_elem.text.strip()
        except Exception:
            logger.warning("[Metadata] Could not extract scope from metadata")

        return None

    @classmethod
    def fetch_edugain_sha1_list(cls):
        """
        Fetch SHA1 hashes of all entities from eduGAIN API

        Returns:
            (success status, dict of {entity_id: [entity_id, sha1, timestamp]} or error message)
        """
        api_url = (
            "https://technical.edugain.org/api?action=list_entity_sha1&format=json"
        )

        logger.info("[Metadata] Fetching SHA1 list from eduGAIN")

        success, content = fetch_url(api_url)

        if not success:
            return False, content

        try:
            data = json.loads(content)
            # Convert to dict for easier lookup: {entity_id: [entity_id, sha1, timestamp]}
            sha1_dict = {item[0]: item for item in data}
            logger.info(
                f"[Metadata] Successfully fetched SHA1 list with {len(sha1_dict)} entities"
            )
            return True, sha1_dict
        except Exception as e:
            error_msg = f"Failed to parse SHA1 list JSON: {str(e)}"
            logger.error(f"[Metadata] {error_msg}")
            return False, error_msg

    @classmethod
    def check_edugain_updates(cls, app=None):
        """
        Check for updates to eduGAIN metadata for ALREADY_IN entities using SHA1 comparison

        Returns:
            dict: Update statistics
        """
        if app is None:
            app = current_app._get_current_object()

        service = cls(app)

        stats = {"checked": 0, "updated": 0, "unchanged": 0, "errors": 0}

        try:
            # Fetch current SHA1 list from eduGAIN
            success, sha1_data = cls.fetch_edugain_sha1_list()
            if not success:
                logger.error(
                    f"[Metadata] Failed to fetch eduGAIN SHA1 list: {sha1_data}"
                )
                stats["errors"] += 1
                return stats

            # Get ALREADY_IN entities
            idps = Idp.query.filter(
                Idp.idp_edugain == EdugainStatus.ALREADY_IN.value
            ).all()
            sps = Sp.query.filter(Sp.sp_edugain == EdugainStatus.ALREADY_IN.value).all()

            # Check IdPs
            for idp in idps:
                try:
                    entity_id = idp.idp_entityid
                    if not entity_id:
                        continue

                    stats["checked"] += 1

                    # Check if entity exists in eduGAIN
                    if entity_id not in sha1_data:
                        logger.warning(
                            f"[Metadata] Entity {entity_id} not found in eduGAIN list"
                        )
                        continue

                    # Get current SHA1 from eduGAIN
                    _, remote_sha1, _ = sha1_data[entity_id]

                    # Compare with stored SHA1
                    if idp.idp_metadata_sha1 == remote_sha1:
                        stats["unchanged"] += 1
                        logger.debug(f"[Metadata] IdP {entity_id} unchanged")
                        continue

                    # Fetch updated metadata from eduGAIN
                    success, content = cls.fetch_edugain_metadata(entity_id)

                    if not success:
                        stats["errors"] += 1
                        logger.error(
                            f"[Metadata] Failed to fetch eduGAIN metadata for {entity_id}: {content}"
                        )
                        continue

                    # Save new metadata
                    service._save_edugain_metadata(
                        idp, content, app.config["STORAGE_ROOT"]
                    )

                    # Update SHA1
                    idp.idp_metadata_sha1 = remote_sha1

                    # Update scope if it's an IdP
                    extracted_scope = cls.extract_scope_from_idp_metadata(content)
                    if extracted_scope:
                        idp.idp_scope = extracted_scope

                    stats["updated"] += 1
                    logger.info(f"[Metadata] Updated eduGAIN metadata for {entity_id}")

                except Exception as e:
                    logger.error(
                        f"[Metadata] Error checking IdP {idp.idp_entityid}: {e}"
                    )
                    stats["errors"] += 1

            # Check SPs
            for sp in sps:
                try:
                    entity_id = sp.sp_entityid
                    if not entity_id:
                        continue

                    stats["checked"] += 1

                    # Check if entity exists in eduGAIN
                    if entity_id not in sha1_data:
                        logger.warning(
                            f"[Metadata] Entity {entity_id} not found in eduGAIN list"
                        )
                        continue

                    # Get current SHA1 from eduGAIN
                    _, remote_sha1, _ = sha1_data[entity_id]

                    # Compare with stored SHA1
                    if sp.sp_metadata_sha1 == remote_sha1:
                        stats["unchanged"] += 1
                        logger.debug(f"[Metadata] SP {entity_id} unchanged")
                        continue

                    # Fetch updated metadata from eduGAIN
                    success, content = cls.fetch_edugain_metadata(entity_id)

                    if not success:
                        stats["errors"] += 1
                        logger.error(
                            f"[Metadata] Failed to fetch eduGAIN metadata for {entity_id}: {content}"
                        )
                        continue

                    # Save new metadata
                    service._save_edugain_metadata(
                        sp, content, app.config["STORAGE_ROOT"]
                    )

                    # Update SHA1
                    sp.sp_metadata_sha1 = remote_sha1

                    stats["updated"] += 1
                    logger.info(f"[Metadata] Updated eduGAIN metadata for {entity_id}")

                except Exception as e:
                    logger.error(f"[Metadata] Error checking SP {sp.sp_entityid}: {e}")
                    stats["errors"] += 1

            # Commit all changes
            db.session.commit()

            logger.info(f"[Metadata] eduGAIN update check completed: {stats}")
            return stats

        except Exception as e:
            logger.error(f"[Metadata] Error in check_edugain_updates: {e}")
            db.session.rollback()
            raise

    # ==========================
    # Private Instance Methods
    # ==========================

    def _save_edugain_metadata(self, entity, content, storage_root):
        """
        Save eduGAIN metadata to file for an entity
        """
        # Generate filename based on entity type and ID
        if isinstance(entity, Idp):
            filename = f"idp-{entity.idp_id}-metadata.xml"
            metadata_attr = "idp_metadata_file"
        else:  # isinstance(entity, Sp)
            filename = f"sp-{entity.sp_id}-metadata.xml"
            metadata_attr = "sp_metadata_file"

        # Create directory if it doesn't exist
        file_path = os.path.join(
            storage_root, "private", "members", str(entity.organization_id), filename
        )
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write metadata file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Update entity metadata file reference
        setattr(
            entity,
            metadata_attr,
            os.path.join("private", "members", str(entity.organization_id), filename),
        )

        # Create transformed copy
        transformed_path = file_path.replace(".xml", "-transformed.xml")
        shutil.copy(file_path, transformed_path)

        return file_path

    def _collect_source_files(self, statuses=None, edugain_only=False):
        """Collect transformed metadata files for entities.
        - statuses: list of status values to include (None means all)
        - edugain_only: if True, only include entities with eduGAIN enabled
        """
        sources = []
        storage_root = self.app.config["STORAGE_ROOT"]

        # IdPs
        query = Idp.query.filter(Idp.idp_metadata_file.isnot(None))
        if statuses is not None:
            query = query.filter(Idp.idp_status.in_(statuses))
        if edugain_only:
            query = query.filter(Idp.idp_edugain == EdugainStatus.YES.value)
        for idp in query.order_by(Idp.idp_entityid).all():
            orig = idp.idp_metadata_file
            transformed = orig.replace(".xml", "-transformed.xml")
            abs_path = os.path.join(storage_root, transformed)
            if os.path.exists(abs_path):
                sources.append((abs_path, "idp"))
            else:
                logger.error(f"[Metadata] Transformed IdP metadata missing: {abs_path}")

        # SPs
        query = Sp.query.filter(Sp.sp_metadata_file.isnot(None))
        if statuses is not None:
            query = query.filter(Sp.sp_status.in_(statuses))
        if edugain_only:
            query = query.filter(Sp.sp_edugain == EdugainStatus.YES.value)
        for sp in query.order_by(Sp.sp_entityid).all():
            orig = sp.sp_metadata_file
            transformed = orig.replace(".xml", "-transformed.xml")
            abs_path = os.path.join(storage_root, transformed)
            if os.path.exists(abs_path):
                sources.append((abs_path, "sp"))
            else:
                logger.error(f"[Metadata] Transformed SP metadata missing: {abs_path}")

        return sources

    def _regenerate(self, output_path_key, statuses=None, edugain_only=False):
        """Regenerate federation metadata file using pyFF pipeline.
        - output_path_key: config key for output path (e.g., 'FEDERATION_METADATA_OUTPUT')
        - statuses: list of status values to include (None means all)
        - edugain_only: if True, only include entities with eduGAIN enabled
        """
        lock_file = os.path.join(tempfile.gettempdir(), "fedadmin-metadata.lock")
        with open(lock_file, "w") as lf:
            try:
                portalocker.lock(lf, portalocker.LOCK_EX | portalocker.LOCK_NB)
            except portalocker.LockException:
                logger.warning(
                    "[Metadata] Another metadata regeneration is already in progress. Skipping."
                )
                return

            try:
                output_path = self.app.config[output_path_key]
                key_path = self.app.config["FEDERATION_SIGNING_KEY"]
                cert_path = self.app.config["FEDERATION_SIGNING_CERT"]

                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                # Get federation name for Name attribute
                federation_name = self.app.config.get("FEDERATION_NAME", "samplefed")
                name_urn = f"urn:mace:shibboleth:{federation_name}"

                # Generate ID like "samplefed20260326023014"
                now = datetime.utcnow()
                id_suffix = now.strftime("%Y%m%d%H%M%S")
                entity_id = f"{federation_name}{id_suffix}"

                # validUntil: now + 28 days
                valid_until = now + timedelta(days=28)
                valid_until_str = valid_until.strftime("%Y-%m-%dT%H:%M:%SZ")

                # Get publisher from federation config
                fed = Federation.query.first()
                publisher = fed.publisher if fed else "https://www.example.com"

                # Generate creation instant for PublicationInfo
                creation_instant = now.isoformat(timespec="seconds") + "Z"

                # Prepare XSLT template with publisher and creation instant replaced
                xslt_template_path = os.path.join(
                    os.path.dirname(__file__),
                    "xslt",
                    "federation-metadata.xsl.template",
                )
                with open(xslt_template_path, "r") as f:
                    xslt_content = f.read()
                xslt_content = xslt_content.replace("PUBLISHER_URL", publisher)
                xslt_content = xslt_content.replace(
                    "CREATION_INSTANT", creation_instant
                )
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".xsl", delete=False
                ) as xslt_file:
                    xslt_file.write(xslt_content)
                xslt_temp_path = xslt_file.name

                empty_xml_file = None
                sources = self._collect_source_files(
                    statuses=statuses, edugain_only=edugain_only
                )
                if not sources:
                    empty_xml = self._create_empty_metadata_xml()
                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".xml", delete=False
                    ) as f:
                        f.write(empty_xml)
                        empty_xml_file = f.name
                    pipeline = [
                        {"load": [f"file://{empty_xml_file}"]},
                        "select",
                        {
                            "finalize": {
                                "validUntil": valid_until_str,
                                "Name": name_urn,
                                "ID": entity_id,
                            }
                        },
                        {"xslt": {"stylesheet": xslt_temp_path}},
                        {"sign": {"key": key_path, "cert": cert_path}},
                        {"publish": output_path},
                    ]
                else:
                    file_urls = [f"file://{path}" for path, _ in sources]
                    pipeline = [
                        {"load": file_urls},
                        "select",
                        {
                            "finalize": {
                                "validUntil": valid_until_str,
                                "Name": name_urn,
                                "ID": entity_id,
                            }
                        },
                        {"xslt": {"stylesheet": xslt_temp_path}},
                        {"sign": {"key": key_path, "cert": cert_path}},
                        {"publish": output_path},
                    ]

                yaml_content = yaml.dump(pipeline, default_flow_style=False)
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".yaml", delete=False
                ) as yf:
                    yf.write(yaml_content)
                    yaml_file = yf.name

                try:
                    cmd = ["pyff", "--loglevel=WARNING", yaml_file]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        error_msg = (
                            f"pyFF failed with exit code {result.returncode}\n"
                            f"STDOUT:\n{result.stdout}\n"
                            f"STDERR:\n{result.stderr}"
                        )
                        logger.error(f"[Metadata] {error_msg}")
                        raise RuntimeError(error_msg)
                finally:
                    if os.path.exists(yaml_file):
                        os.unlink(yaml_file)

                logger.info(
                    f"[Metadata] Federation metadata regenerated to {output_path}"
                )

            finally:
                portalocker.unlock(lf)
                # Clean temp files
                for f in [empty_xml_file, xslt_temp_path]:
                    if f and os.path.exists(f):
                        try:
                            os.unlink(f)
                        except OSError:
                            pass

    def _transform_entity(self, entity_type, entity_id, original_path, organization_id):
        """Convert original entity metadata to federation format, saved as '-transformed.xml'."""
        if not os.path.exists(original_path):
            raise FileNotFoundError(f"Original metadata not found: {original_path}")

        tree = etree.parse(original_path)
        root = tree.getroot()

        self._ensure_namespaces(root)

        fed = Federation.query.first()
        if not fed:
            logger.warning(
                "[Metadata] Federation configuration not found, skipping registration info"
            )
        org = Organization.query.get(organization_id)
        if not org:
            raise ValueError(f"Organization {organization_id} not found")

        if entity_type == "idp":
            entity = Idp.query.get(entity_id)
        else:
            entity = Sp.query.get(entity_id)
        if not entity:
            raise ValueError(f"{entity_type.upper()} {entity_id} not found")

        self._add_registration_info(root, fed)
        if entity_type == "idp":
            self._ensure_scope(root, entity)
        self._add_ui_info(root, entity, entity_type, org)
        self._add_organization(root, org)
        self._add_contacts(root, entity)
        self._add_security_contact(root, entity)
        self._add_entity_attributes(root, entity, entity_type)

        # Remove validUntil parameter if it exists
        self._remove_valid_until(root)

        # Remove comments
        etree.strip_elements(root, etree.Comment)

        # Indent the XML tree for better readability
        etree.indent(root, space="  ")

        transformed_path = original_path.replace(".xml", "-transformed.xml")
        tree.write(
            transformed_path, encoding="UTF-8", xml_declaration=False, pretty_print=True
        )
        logger.info(f"[Metadata] Transformed metadata saved to {transformed_path}")
        return transformed_path

    def _retransform_all_entities(self):
        """Re-transform all non-ALREADY_IN entities with new federation configuration."""
        lock_file = os.path.join(tempfile.gettempdir(), "fedadmin-transform-all.lock")
        with open(lock_file, "w") as lf:
            try:
                portalocker.lock(lf, portalocker.LOCK_EX | portalocker.LOCK_NB)
            except portalocker.LockException:
                logger.warning(
                    "[Metadata] Another full re-transformation is already in progress. Skipping."
                )
                return

            try:
                storage_root = self.app.config["STORAGE_ROOT"]
                count = 0

                # Process IdPs
                idps = Idp.query.filter(
                    Idp.idp_metadata_file.isnot(None),
                    Idp.idp_edugain != EdugainStatus.ALREADY_IN.value,
                ).all()

                for idp in idps:
                    try:
                        self._transform_entity(
                            "idp",
                            idp.idp_id,
                            os.path.join(storage_root, idp.idp_metadata_file),
                            idp.organization_id,
                        )
                        count += 1
                    except Exception as e:
                        logger.error(
                            f"[Metadata] Failed to re-transform IdP #{idp.idp_id}: {e}"
                        )

                # Process SPs
                sps = Sp.query.filter(
                    Sp.sp_metadata_file.isnot(None),
                    Sp.sp_edugain != EdugainStatus.ALREADY_IN.value,
                ).all()

                for sp in sps:
                    try:
                        self._transform_entity(
                            "sp",
                            sp.sp_id,
                            os.path.join(storage_root, sp.sp_metadata_file),
                            sp.organization_id,
                        )
                        count += 1
                    except Exception as e:
                        logger.error(
                            f"[Metadata] Failed to re-transform SP #{sp.sp_id}: {e}"
                        )

                logger.info(f"[Metadata] Successfully re-transformed {count} entities.")

                # Always regenerate federation metadata after re-transforming all entities
                logger.info(
                    "[Metadata] Now regenerating federation metadata with updated entities."
                )
                self._regenerate(
                    output_path_key="FEDERATION_METADATA_BETA_OUTPUT",
                    statuses=[EntityStatus.INIT.value, EntityStatus.APPROVING.value],
                )
                self._regenerate(
                    output_path_key="FEDERATION_METADATA_OUTPUT",
                    statuses=[EntityStatus.READY.value],
                )
                self._regenerate(
                    output_path_key="FEDERATION_METADATA_EDUGAIN_OUTPUT",
                    statuses=[EntityStatus.READY.value],
                    edugain_only=True,
                )
                logger.info("[Metadata] Federation metadata regeneration completed.")

            finally:
                portalocker.unlock(lf)

    # ==========================
    # Private helper methods
    # ==========================

    def _remove_valid_until(self, root):
        """Remove validUntil attribute from EntityDescriptor if it exists."""
        ns = {"md": self.NAMESPACES["md"]}
        # If root is already EntityDescriptor, use it directly
        if root.tag == f"{{{self.NAMESPACES['md']}}}EntityDescriptor":
            entity = root
        else:
            entity = root.find("md:EntityDescriptor", namespaces=ns)

        if entity is not None and "validUntil" in entity.attrib:
            del entity.attrib["validUntil"]

    def _ensure_namespaces(self, root):
        """Register required namespaces (so they appear in output)."""
        for prefix, uri in self.NAMESPACES.items():
            etree.register_namespace(prefix, uri)

    def _get_or_create_extensions(self, parent):
        """Get Extensions element under parent; create if it doesn't exist."""
        ns = {"md": self.NAMESPACES["md"]}
        ext = parent.find("md:Extensions", namespaces=ns)
        if ext is None:
            ext = etree.SubElement(parent, f"{{{self.NAMESPACES['md']}}}Extensions")
        return ext

    def _add_registration_info(self, root, fed):
        """Add mdrpi:RegistrationInfo to root Extensions, and ensure Extensions
        is the first child of the root element, with RegistrationInfo as the
        first child of Extensions.
        """
        if not fed:
            return
        ns = {"mdrpi": self.NAMESPACES["mdrpi"]}
        extensions = self._get_or_create_extensions(root)

        # Move Extensions to the first position under root
        root.insert(0, extensions)

        # Remove any existing RegistrationInfo
        for ri in extensions.findall("mdrpi:RegistrationInfo", namespaces=ns):
            extensions.remove(ri)

        ri = etree.SubElement(
            extensions, f"{{{self.NAMESPACES['mdrpi']}}}RegistrationInfo"
        )
        ri.set("registrationAuthority", fed.registration_authority)
        ri.set(
            "registrationInstant", datetime.utcnow().isoformat(timespec="seconds") + "Z"
        )

        if fed.registration_policy_url:
            policy = etree.SubElement(
                ri, f"{{{self.NAMESPACES['mdrpi']}}}RegistrationPolicy"
            )
            policy.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
            policy.text = fed.registration_policy_url

        # Move RegistrationInfo to the first position in Extensions
        extensions.insert(0, ri)

    def _add_ui_info(self, root, entity, entity_type, org):
        """Add mdui:UIInfo to IDPSSODescriptor or SPSSODescriptor Extensions."""
        ns = {"md": self.NAMESPACES["md"]}
        if entity_type == "idp":
            desc = root.find(".//md:IDPSSODescriptor", namespaces=ns)
        else:
            desc = root.find(".//md:SPSSODescriptor", namespaces=ns)
        if desc is None:
            logger.warning(
                f"[Metadata] No {entity_type.upper()}SSODescriptor found, skipping UIInfo"
            )
            return

        extensions = self._get_or_create_extensions(desc)
        for ui in extensions.findall(
            "mdui:UIInfo", namespaces={"mdui": self.NAMESPACES["mdui"]}
        ):
            extensions.remove(ui)

        ui = etree.SubElement(extensions, f"{{{self.NAMESPACES['mdui']}}}UIInfo")

        # DisplayName
        display_name = entity.idp_name if entity_type == "idp" else entity.sp_name
        if display_name:
            dn = etree.SubElement(ui, f"{{{self.NAMESPACES['mdui']}}}DisplayName")
            dn.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
            dn.text = display_name

        # Description
        description = (
            entity.idp_description if entity_type == "idp" else entity.sp_description
        )
        if description:
            desc_elem = etree.SubElement(
                ui, f"{{{self.NAMESPACES['mdui']}}}Description"
            )
            desc_elem.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
            desc_elem.text = description

        # Logo
        logo_url = entity.idp_logo if entity_type == "idp" else entity.sp_logo
        if logo_url:
            logo = etree.SubElement(ui, f"{{{self.NAMESPACES['mdui']}}}Logo")
            logo.set("width", "80")
            logo.set("height", "80")
            logo.text = logo_url

        # Information URL (for SP)
        if (
            entity_type == "sp"
            and hasattr(entity, "information_url")
            and entity.information_url
        ):
            info_url = etree.SubElement(
                ui, f"{{{self.NAMESPACES['mdui']}}}InformationURL"
            )
            info_url.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
            info_url.text = entity.information_url

        # Privacy Statement URL (for SP)
        if (
            entity_type == "sp"
            and hasattr(entity, "privacy_statement_url")
            and entity.privacy_statement_url
        ):
            privacy = etree.SubElement(
                ui, f"{{{self.NAMESPACES['mdui']}}}PrivacyStatementURL"
            )
            privacy.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
            privacy.text = entity.privacy_statement_url

    def _add_organization(self, root, org):
        """Add Organization element to EntityDescriptor."""
        if not org.organization_name:
            return
        ns = {"md": self.NAMESPACES["md"]}
        existing = root.find("md:Organization", namespaces=ns)
        if existing is not None:
            root.remove(existing)

        org_elem = etree.SubElement(root, f"{{{self.NAMESPACES['md']}}}Organization")

        name = etree.SubElement(
            org_elem, f"{{{self.NAMESPACES['md']}}}OrganizationName"
        )
        name.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
        name.text = org.organization_name

        disp = etree.SubElement(
            org_elem, f"{{{self.NAMESPACES['md']}}}OrganizationDisplayName"
        )
        disp.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
        disp.text = org.organization_name  # Can be extended with separate field later

        if org.organization_url:
            url_elem = etree.SubElement(
                org_elem, f"{{{self.NAMESPACES['md']}}}OrganizationURL"
            )
            url_elem.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
            url_elem.text = org.organization_url

    def _add_contacts(self, root, entity):
        """Add ContactPerson (technical) to EntityDescriptor."""
        if not (entity.contact_technical_name and entity.contact_technical_email):
            return
        ns = {"md": self.NAMESPACES["md"]}
        # Remove any existing ContactPerson elements
        for contact in root.findall("md:ContactPerson", namespaces=ns):
            root.remove(contact)

        contact = etree.SubElement(root, f"{{{self.NAMESPACES['md']}}}ContactPerson")
        contact.set("contactType", "technical")
        given_name = etree.SubElement(contact, f"{{{self.NAMESPACES['md']}}}GivenName")
        given_name.text = entity.contact_technical_name
        email = etree.SubElement(contact, f"{{{self.NAMESPACES['md']}}}EmailAddress")
        email.text = f"mailto:{entity.contact_technical_email}"

    def _add_security_contact(self, root, entity):
        """Add security contact for Sirtfi-compliant entities."""
        if not entity.sirtfi_enabled:
            return
        if not (entity.security_contact_name and entity.security_contact_email):
            return

        ns = {"md": self.NAMESPACES["md"], "remd": self.NAMESPACES["remd"]}
        # Remove existing security contact to avoid duplicates
        for contact in root.findall("md:ContactPerson", namespaces=ns):
            if contact.get("contactType") == "other":
                # Check if it has remd:contactType security
                remd_type = contact.get(f"{{{self.NAMESPACES['remd']}}}contactType")
                if remd_type == "http://refeds.org/metadata/contactType/security":
                    root.remove(contact)

        contact = etree.SubElement(root, f"{{{self.NAMESPACES['md']}}}ContactPerson")
        contact.set("contactType", "other")
        contact.set(
            f"{{{self.NAMESPACES['remd']}}}contactType",
            "http://refeds.org/metadata/contactType/security",
        )

        given_name = etree.SubElement(contact, f"{{{self.NAMESPACES['md']}}}GivenName")
        given_name.text = entity.security_contact_name

        email = etree.SubElement(contact, f"{{{self.NAMESPACES['md']}}}EmailAddress")
        email.text = f"mailto:{entity.security_contact_email}"

    def _add_entity_attributes(self, root, entity, entity_type):
        """Add REFEDS entity category attributes (R&S, CoCo) and assurance certification (Sirtfi)."""
        # Determine if any attributes are to be added
        has_rs = entity.rs_enabled
        has_coco = (
            entity_type == "sp"
            and hasattr(entity, "coco_enabled")
            and entity.coco_enabled
        )
        has_sirtfi = entity.sirtfi_enabled

        if not (has_rs or has_coco or has_sirtfi):
            return

        # Find or create Extensions element
        extensions = self._get_or_create_extensions(root)

        # Remove existing EntityAttributes to avoid duplication
        for attr in extensions.findall(
            "mdattr:EntityAttributes", namespaces={"mdattr": self.NAMESPACES["mdattr"]}
        ):
            extensions.remove(attr)

        # Create a single EntityAttributes element
        entity_attrs = etree.SubElement(
            extensions, f"{{{self.NAMESPACES['mdattr']}}}EntityAttributes"
        )

        # Add R&S (different for IdP and SP)
        if has_rs:
            if entity_type == "sp":
                attr_name = "http://macedir.org/entity-category"
            else:  # idp
                attr_name = "http://macedir.org/entity-category-support"

            attr = etree.SubElement(
                entity_attrs, f"{{{self.NAMESPACES['saml']}}}Attribute"
            )
            attr.set("Name", attr_name)
            attr.set("NameFormat", "urn:oasis:names:tc:SAML:2.0:attrname-format:uri")
            value = etree.SubElement(
                attr, f"{{{self.NAMESPACES['saml']}}}AttributeValue"
            )
            value.text = "http://refeds.org/category/research-and-scholarship"

        # Add CoCo (only for SP)
        if has_coco:
            attr = etree.SubElement(
                entity_attrs, f"{{{self.NAMESPACES['saml']}}}Attribute"
            )
            attr.set("Name", "http://macedir.org/entity-category")
            attr.set("NameFormat", "urn:oasis:names:tc:SAML:2.0:attrname-format:uri")
            value = etree.SubElement(
                attr, f"{{{self.NAMESPACES['saml']}}}AttributeValue"
            )
            value.text = "http://refeds.org/category/code-of-conduct"

        # Add Sirtfi (assurance certification)
        if has_sirtfi:
            attr = etree.SubElement(
                entity_attrs, f"{{{self.NAMESPACES['saml']}}}Attribute"
            )
            attr.set(
                "Name", "urn:oasis:names:tc:SAML:attribute:assurance-certification"
            )
            attr.set("NameFormat", "urn:oasis:names:tc:SAML:2.0:attrname-format:uri")
            value = etree.SubElement(
                attr, f"{{{self.NAMESPACES['saml']}}}AttributeValue"
            )
            value.text = "https://refeds.org/sirtfi"

    def _ensure_scope(self, root, idp):
        """Ensure IdP's shibmd:Scope exists and is correct."""
        ns = {"md": self.NAMESPACES["md"]}
        idp_desc = root.find(".//md:IDPSSODescriptor", namespaces=ns)
        if idp_desc is None:
            return
        extensions = self._get_or_create_extensions(idp_desc)
        shib_ns = {"shibmd": self.NAMESPACES["shibmd"]}
        for scope in extensions.findall("shibmd:Scope", namespaces=shib_ns):
            extensions.remove(scope)

        if idp.idp_scope:
            scope = etree.SubElement(
                extensions, f"{{{self.NAMESPACES['shibmd']}}}Scope"
            )
            scope.set("regexp", "false")
            scope.text = idp.idp_scope

    def _generate_id(self) -> str:
        """Generate a random ID attribute value."""
        return f"_{uuid.uuid4().hex}"

    def _create_empty_metadata_xml(self) -> str:
        """Generate a placeholder empty metadata XML (containing minimal elements)."""
        root = etree.Element(f"{{{self.NAMESPACES['md']}}}EntitiesDescriptor")
        root.attrib["ID"] = self._generate_id()

        entity = etree.SubElement(root, f"{{{self.NAMESPACES['md']}}}EntityDescriptor")
        entity.attrib["entityID"] = "https://placeholder.fedadmin.example.com"

        sp_sso = etree.SubElement(entity, f"{{{self.NAMESPACES['md']}}}SPSSODescriptor")
        sp_sso.attrib["protocolSupportEnumeration"] = (
            "urn:oasis:names:tc:SAML:2.0:protocol"
        )

        acs = etree.SubElement(
            sp_sso, f"{{{self.NAMESPACES['md']}}}AssertionConsumerService"
        )
        acs.attrib["Binding"] = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        acs.attrib["Location"] = "https://placeholder.fedadmin.example.com/acs"
        acs.attrib["index"] = "0"

        return etree.tostring(
            root, pretty_print=True, xml_declaration=False, encoding="UTF-8"
        ).decode("utf-8")
