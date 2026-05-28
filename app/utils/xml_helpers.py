from lxml import etree


def safe_xml_parser():
    """Create a conservative XML parser for untrusted metadata."""
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        huge_tree=False,
    )


def safe_fromstring(content):
    """Parse XML bytes or text without resolving external entities or network resources."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return etree.fromstring(content, parser=safe_xml_parser())


def safe_parse(path):
    """Parse an XML file with the same restrictions as safe_fromstring."""
    return etree.parse(path, parser=safe_xml_parser())
