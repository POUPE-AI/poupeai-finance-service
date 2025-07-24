import requests
import jwt
from django.conf import settings
from django.core.cache import cache
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import HTTP_HEADER_ENCODING
from poupeai_finance_service.profiles.models import Profile
from poupeai_finance_service.bank_accounts.models import BankAccount
from django.utils.translation import gettext_lazy as _

class KeycloakSubProfileAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = self.get_authorization_header(request)
        if not auth_header:
            return None
            
        try:
            token = self.extract_token(auth_header)
            payload = self.validate_token(token)
            profile = self.get_or_create_profile(payload)
            return (profile, token)
        except AuthenticationFailed:
            raise
        except Exception as e:
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
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError as e:
            raise AuthenticationFailed(f'Invalid token: {str(e)}')
        except Exception as e:
            raise AuthenticationFailed(f'Token validation failed: {str(e)}')
    
    def get_jwks(self):
        cache_key = 'keycloak_jwks'
        jwks = cache.get(cache_key)
        
        if not jwks:
            try:
                response = requests.get(settings.KEYCLOAK_JWKS_URL, timeout=10)
                response.raise_for_status()
                jwks = response.json()
                cache.set(cache_key, jwks, 3600)
            except requests.RequestException as e:
                raise AuthenticationFailed(f'Failed to fetch JWKS: {str(e)}')
        
        return jwks
    
    def get_or_create_profile(self, payload):
        user_id = payload.get('sub')
        email = payload.get('email')
        first_name = payload.get('given_name', '')
        last_name = payload.get('family_name', '')
        
        if not user_id:
            raise AuthenticationFailed('Token missing sub claim')
        
        if not email:
            raise AuthenticationFailed('Token missing email claim')
        
        profile, created = Profile.objects.get_or_create(
            user_id=user_id,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            }
        )
        
        if not created:
            fields_to_update = {}
            if profile.email != email:
                fields_to_update['email'] = email
            if profile.first_name != first_name:
                fields_to_update['first_name'] = first_name
            if profile.last_name != last_name:
                fields_to_update['last_name'] = last_name
            
            if fields_to_update:
                for field, value in fields_to_update.items():
                    setattr(profile, field, value)
                profile.save(update_fields=list(fields_to_update.keys()))
        
        if created:
            self.create_default_bank_account(profile)
        
        return profile
    
    def create_default_bank_account(self, profile):
        try:
            BankAccount.objects.create(
                profile=profile,
                name=_('Minha Carteira'),
                is_default=True
            )
        except Exception as e:
            print(f"Failed to create default bank account for profile {profile.user_id}: {str(e)}")
    
    def authenticate_header(self, request):
        return 'Bearer realm="keycloak"' 