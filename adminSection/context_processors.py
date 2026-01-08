from .models import Profile
import logging

logger = logging.getLogger(__name__)

def user_role_context(request):
    if not request.user.is_authenticated:
        logger.debug("User is not authenticated")
        return {}

    try:
        profile = Profile.objects.get(user=request.user)
        logger.debug(f"Profile found: user_type={profile.user_type}")
        return {'user_role': profile.user_type}
    except Profile.DoesNotExist:
        if request.user.is_superuser:
            logger.debug("User is superuser, setting user_role to 'admin'")
            return {'user_role': 'admin'}
        logger.debug("No profile found and user is not superuser")
        return {}