# -*- coding: utf-8 -*-
from gluon.tools import PluginManager
from plugin_social_auth.utils import SocialAuth

# Remove this in production
from gluon.custom_import import track_changes; track_changes(True)

# This needs to be replaced by your own db connection
db = DAL('mongodb://localhost/test')

auth = SocialAuth(db)
plugins = PluginManager()

# Enable the "username" field
auth.define_tables(username=True)

# Disable certain auth actions unless you're also using web2py account registration
auth.settings.actions_disabled = ['register', 'change_password', 'request_reset_password']

# Configure where to redirect to after logout.
# If you do not configure this, web2py by default redirects to the index action of the
# controller configured for auth. If you are using {{{SocialAuth}}} unmodified, you will be
# redirected to the index action of the plugin controller which will redirect to the login page OR
# if you configure the setting SOCIAL_AUTH_APP_INDEX_URL, to you app index page.
# auth.settings.logout_next = URL()

# Make user props readonly since these will automatically be updated
# when the user logs on with a new social account anyway.
# NOTE: this fails when lazy tables used.
for prop in ['first_name', 'last_name', 'username', 'email']:
    auth.settings.table_user[prop].writable = False

############################################################################
##
## w2p-social-auth plugin configuration
##
############################################################################

# Configure your API keys
# This needs to be replaced by your actual API keys
plugins.social_auth.SOCIAL_AUTH_TWITTER_KEY = settings.twitter_consumer_key
plugins.social_auth.SOCIAL_AUTH_TWITTER_SECRET = settings.twitter_consumer_secret
plugins.social_auth.SOCIAL_AUTH_FACEBOOK_KEY = settings.facebook_app_id
plugins.social_auth.SOCIAL_AUTH_FACEBOOK_SECRET = settings.facebook_app_secret
plugins.social_auth.SOCIAL_AUTH_LIVE_KEY = settings.live_client_id
plugins.social_auth.SOCIAL_AUTH_LIVE_SECRET = settings.live_client_secret

# Configure PSA with all required backends
# Replace this by the backends that you want to use and have API keys for
plugins.social_auth.SOCIAL_AUTH_AUTHENTICATION_BACKENDS = (
    # You need this one to enable manual input for openid.
    # It must _not_ be configured in SOCIAL_AUTH_PROVIDERS (below)
    'social.backends.open_id.OpenIdAuth',

    'social.backends.persona.PersonaAuth',
    'social.backends.live.LiveOAuth2',
    'social.backends.twitter.TwitterOAuth',
    'social.backends.facebook.FacebookOAuth2')

# Configure the providers that you want to show in the login form.
# <backend name> : <display name>
# (You can find the backend name in the backend files as configured above.)
# Replace this by the backends you want to enable
plugins.social_auth.SOCIAL_AUTH_PROVIDERS = {
    'live': 'Live',
    'twitter': 'Twitter',
    'facebook': 'Facebook',
    'persona': 'Mozilla Persona'}

# Remove or set to False if you are not using Persona
plugins.social_auth.SOCIAL_AUTH_ENABLE_PERSONA = True

