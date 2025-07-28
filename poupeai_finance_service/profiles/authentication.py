import requests
import jwt
import structlog
from django.conf import settings
from django.core.cache import cache
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import HTTP_HEADER_ENCODING
from poupeai_finance_service.profiles.models import Profile
from poupeai_finance_service.bank_accounts.models import BankAccount
from poupeai_finance_service.core.events import EventType
from django.utils.translation import gettext_lazy as _

log = structlog.get_logger(__name__)

class KeycloakSubProfileAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = self.get_authorization_header(request)
        if not auth_header:
            return None
            
        try:
            token = self.extract_token(auth_header)
            payload = self.validate_token(token)
            profile = self.get_or_create_profile(payload)
            
            log.info(
                "User authentication successful",
                event_type=EventType.AUTHENTICATION_SUCCESS,
                actor_user_id=profile.user_id
            )
            return (profile, token)
        
        except AuthenticationFailed as e:
            log.warning(
                "Authentication attempt failed",
                event_type=EventType.AUTHENTICATION_FAILED,
                event_details={"reason": str(e)}
            )
            raise
        except Exception as e:
            log.error(
                "An unexpected error occurred during authentication",
                event_type=EventType.AUTHENTICATION_FAILED,
                exc_info=e
            )
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')
    
    def get_authorization_header(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION', b'')
        if isinstance(auth, str):
            auth = auth.encode(HTTP_HEADER_ENCODING)
        return auth
    
    def extract_token(self, auth_header):
        auth_header = auth_header.decode(HTTP_HEADER_ENCODING)
        parts = auth_header.split()
        
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise AuthenticationFailed('Invalid authorization header format')
        
        return parts[1]
    
    def validate_token(self, token):
        try:
            jwks = self.get_jwks()
            
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')
            
            if not kid:
                raise AuthenticationFailed('Token missing kid in header')
            
            key = None
            for jwk in jwks['keys']:
                if jwk['kid'] == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                    break
            
            if not key:
                raise AuthenticationFailed('Unable to find appropriate key')
            
            payload = jwt.decode(
                token,
                key,
                algorithms=['RS256'],
                audience=settings.KEYCLOAK_AUDIENCE,
                issuer=settings.KEYCLOAK_ISSUER,
                options={'verify_exp': True}
            )
            
            return payload
            
        except jwt.ExpiredSignatureError as e:
            log.warning("Token validation failed: expired signature", event_type=EventType.TOKEN_VALIDATION_FAILED)
            raise AuthenticationFailed('Token has expired') from e
        except jwt.InvalidTokenError as e:
            log.warning("Token validation failed", event_type=EventType.TOKEN_VALIDATION_FAILED, event_details={"reason": str(e)})
            raise AuthenticationFailed(f'Invalid token: {str(e)}') from e
        except Exception as e:
            log.error("Unexpected error during token validation", event_type=EventType.TOKEN_VALIDATION_FAILED, exc_info=e)
            raise AuthenticationFailed(f'Token validation failed: {str(e)}') from e
    
    def get_jwks(self):
        cache_key = 'keycloak_jwks'
        jwks = cache.get(cache_key)
        
        if not jwks:
            log.info("JWKS not found in cache. Fetching from Keycloak.")
            try:
                response = requests.get(settings.KEYCLOAK_JWKS_URL, timeout=10)
                response.raise_for_status()
                jwks = response.json()
                cache.set(cache_key, jwks, 3600)
                log.info("JWKS successfully fetched and cached.")
            except requests.RequestException as e:
                log.error("Failed to fetch JWKS from Keycloak", event_type=EventType.JWKS_FETCH_FAILED, exc_info=e)
                raise AuthenticationFailed(f'Failed to fetch JWKS: {str(e)}') from e
        
        return jwks
    
    def get_or_create_profile(self, payload):
        user_id = payload.get('sub')
        email = payload.get('email')
        first_name = payload.get('given_name', '')
        last_name = payload.get('family_name', '')
        
        if not user_id or not email:
            raise AuthenticationFailed('Token missing required claims (sub or email)')
        
        profile, created = Profile.objects.get_or_create(
            user_id=user_id,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            }
        )
        
        if created:
            log.info("New user profile created from token", event_type=EventType.PROFILE_CREATED_FROM_TOKEN, actor_user_id=user_id)
            self.create_default_bank_account(profile)
        else:
            fields_to_update = {}
            if profile.email != email: fields_to_update['email'] = email
            if profile.first_name != first_name: fields_to_update['first_name'] = first_name
            if profile.last_name != last_name: fields_to_update['last_name'] = last_name
            
            if fields_to_update:
                log.info(
                    "User profile updated from token",
                    event_type=EventType.PROFILE_UPDATED_FROM_TOKEN,
                    actor_user_id=user_id,
                    event_details={"updated_fields": list(fields_to_update.keys())}
                )
                for field, value in fields_to_update.items():
                    setattr(profile, field, value)
                profile.save(update_fields=list(fields_to_update.keys()))
        
        return profile
    
    def create_default_bank_account(self, profile):
        try:
            BankAccount.objects.create(
                profile=profile,
                name=_('Minha Carteira'),
                is_default=True
            )
            log.info("Default bank account created for new user.", actor_user_id=profile.user_id)
        except Exception as e:
            log.error(
                "Failed to create default bank account for new profile",
                event_type=EventType.DEFAULT_BANK_ACCOUNT_CREATION_FAILED,
                actor_user_id=profile.user_id,
                exc_info=e
            )
    
    def authenticate_header(self, request):
        return 'Bearer realm="keycloak"'