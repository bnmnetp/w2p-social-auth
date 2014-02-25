from social.strategies.utils import get_strategy
from social.utils import setting_name
from social.backends.utils import load_backends
from models import User
from functools import wraps
from gluon.html import *
from gluon.http import HTTP, redirect
from gluon.globals import current
from gluon.tools import Auth, addrow


DEFAULT = lambda: None
class SocialAuth(Auth):
    def __init__(self, environment):
        Auth.__init__(self, environment, db=None)

    def social_form(self, remember_me_form=True):
        backends = load_backends(current.plugin_social_auth.plugin.SOCIAL_AUTH_AUTHENTICATION_BACKENDS)

        div = DIV()

        if  remember_me_form:
            # adds a new input checkbox "remember me (for .. days)"
            div.append(DIV(XML("&nbsp;"),
                       INPUT(_type='checkbox',
                             _class='checkbox',
                             _id="auth_user_remember",
                             _name="remember"),
                       XML("&nbsp;&nbsp;"),
                       LABEL(self.messages.label_remember_me,
                             _for="auth_user_remember")))

        select = SELECT(_name='backend')
        for backend in sorted(backends.iterkeys()):
            select.append(OPTION(backend, _value=backend))

        div.append(select)
        div.append(INPUT(_type='hidden', _name='next',_value=self.get_vars_next()))
        div.append(INPUT(_value=current.plugin_social_auth.T(self.messages.login_button), _type='submit'))

        return div

    @staticmethod
    def login_links():
        """ Simple View that shows a login link for every configured backend.
        """
        return current.response.render('plugin_social_auth/login.html')

    def login_form(self, remember_me_form=True):
        return FORM(self.social_form(self.settings.remember_me_form and remember_me_form),
                    _action=URL('plugin_social_auth', 'auth_'))

    def social_login(self, next=DEFAULT):
        # Hide auth navbar
        self.navbar = lambda **x: ''

        return self.login_form()

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

def login_user(user):
    auth = current.plugin_social_auth.auth
    session = current.plugin_social_auth.session

    # login the user
    auth.login_user(user)

    # Check remember settings and configure auth accordingly
    remember = current.strategy.session_get('remember', default=False)
    session.auth.expiration = \
        remember and \
        auth.settings.long_expiration or \
        auth.settings.expiration
    session.auth.remember = remember

    auth.log_event(auth.messages['login_log'], user)

    session.flash = auth.messages.logged_in
