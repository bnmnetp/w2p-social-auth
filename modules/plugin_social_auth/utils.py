from social.strategies.utils import get_strategy
from social.utils import setting_name
from models import User
from functools import wraps
from gluon.html import *
from gluon.http import HTTP, redirect
from gluon.globals import current
from gluon.tools import Auth


DEFAULT = lambda: None
class SocialAuth(Auth):
    def __init__(self, environment):
        Auth.__init__(self, environment, db=None)

    def social_login(self, next=DEFAULT):
        self.navbar = lambda **x: ''

        return current.response.render('plugin_social_auth/login.html')

    def __call__(self):
        request = self.environment.request
        args = request.args
        if not args:
            redirect(URL(r=request, args='login'))
        if args[0] == 'login':
            return self.social_login()
        elif args[0] == 'logout':
            return self.logout()
        elif args[0] == 'groups':
            return self.groups()
        else:
            raise HTTP(404)

def load_strategy(*args, **kwargs):
    return get_strategy(getattr(current.plugin_social_auth.plugin, setting_name('AUTHENTICATION_BACKENDS')),
                        'plugin_social_auth.w2p_strategy.W2PStrategy',
                        'plugin_social_auth.models.W2PStorage',
                        *args, **kwargs)

def url_for(uri, backend):
    return uri + ('?backend=%s' % backend)

def strategy(redirect_uri=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            uri = redirect_uri
            backend = current.request.vars['backend']
            current.strategy = load_strategy(request=current.request,
                                             backend=backend,
                                             redirect_uri=url_for(uri, backend),
                                             *args, **kwargs)
            return func(*args, **kwargs)
        return wrapper
    return decorator

def get_current_user():
    user = current.plugin_social_auth.auth.user
    if user:
        return User(user)