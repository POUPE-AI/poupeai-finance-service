from django.conf import settings
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError
import logging

logger = logging.getLogger(__name__)

def get_keycloak_admin_client() -> KeycloakAdmin | None:
    try:
        return KeycloakAdmin(
            server_url=settings.KEYCLOAK_SERVER_URL,
            client_id=settings.KEYCLOAK_ADMIN_CLIENT_ID,
            client_secret_key=settings.KEYCLOAK_ADMIN_CLIENT_SECRET,
            realm_name=settings.KEYCLOAK_REALM_NAME,
            user_realm_name=settings.KEYCLOAK_REALM_NAME,
            verify=True,
        )
    except Exception as e:
        logger.error(f"Failed to initialize Keycloak admin client: {e}")
        return None

def delete_keycloak_user(user_id: str) -> bool:
    keycloak_admin = get_keycloak_admin_client()
    if not keycloak_admin:
        return False

    try:
        logger.info(f"Attempting to delete user {user_id} from Keycloak.")
        keycloak_admin.delete_user(user_id=user_id)
        logger.info(f"Successfully deleted user {user_id} from Keycloak.")
        return True
    except KeycloakError as e:
        if e.response_code == 404:
            logger.warning(f"User {user_id} not found in Keycloak. Assuming already deleted.")
            return True
        logger.error(f"Error deleting user {user_id} from Keycloak: {e}")
        return False