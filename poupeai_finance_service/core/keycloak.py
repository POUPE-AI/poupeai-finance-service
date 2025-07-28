import structlog
from django.conf import settings
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError
from poupeai_finance_service.core.events import EventType

log = structlog.get_logger(__name__)

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
        log.error(
            "Failed to initialize Keycloak admin client",
            event_type=EventType.KEYCLOAK_ADMIN_CLIENT_INIT_FAILED,
            exc_info=e
        )
        return None

def delete_keycloak_user(user_id: str) -> bool:
    keycloak_admin = get_keycloak_admin_client()
    if not keycloak_admin:
        return False

    try:
        log.info(f"Attempting to delete user {user_id} from Keycloak.")
        keycloak_admin.delete_user(user_id=user_id)
        
        log.info(
            "Successfully deleted user from Keycloak",
            event_type=EventType.KEYCLOAK_USER_DELETION_SUCCESS,
            event_details={"keycloak_user_id": user_id}
        )
        return True
    
    except KeycloakError as e:
        if e.response_code == 404:
            log.warning(
                "User not found in Keycloak. Assuming already deleted.",
                event_type=EventType.KEYCLOAK_USER_DELETION_NOT_FOUND,
                event_details={"keycloak_user_id": user_id}
            )
            return True
            
        log.error(
            "Error deleting user from Keycloak",
            event_type=EventType.KEYCLOAK_USER_DELETION_ERROR,
            event_details={"keycloak_user_id": user_id, "error_code": e.response_code},
            exc_info=e
        )
        return False