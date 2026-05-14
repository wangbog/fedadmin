import logging
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

logger = logging.getLogger(__name__)


def fetch_url(url, timeout=10, verify_ssl=True, headers=None):
    """
    Generic HTTP GET request utility

    Args:
        url: Request URL
        timeout: Timeout in seconds
        verify_ssl: Whether to verify SSL certificate
        headers: Custom request headers

    Returns:
        (success status, content or error message)
    """
    default_headers = {
        "User-Agent": "FedAdmin/1.0 (https://github.com/wangbog/fedadmin)"
    }

    if headers:
        default_headers.update(headers)

    try:
        response = requests.get(
            url, timeout=timeout, verify=verify_ssl, headers=default_headers
        )
        response.raise_for_status()
        return True, response.text

    except Timeout:
        error_msg = f"Request timed out ({timeout}s): {url}"
        logger.error(f"[HTTP] {error_msg}")
        return False, error_msg

    except ConnectionError:
        error_msg = f"Could not establish connection: {url}"
        logger.error(f"[HTTP] {error_msg}")
        return False, error_msg

    except RequestException as e:
        error_msg = f"Request failed: {str(e)}"
        logger.error(f"[HTTP] {error_msg}")
        return False, error_msg
