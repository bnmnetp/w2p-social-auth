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

    def login_form(self):
        settings = self.settings
        T = current.plugin_social_auth.T

        form = FORM(
            _action=URL('plugin_social_auth', 'auth_')
        )

        backends = load_backends(current.plugin_social_auth.plugin.SOCIAL_AUTH_AUTHENTICATION_BACKENDS)

        select = SELECT(_name='backend')
        for backend in backends:
            select.append(OPTION(backend, _value=backend))
        form.append(select)
        form.append(INPUT(_type='hidden', _name='next',_value=self.get_vars_next()))
        form.append(INPUT(_value=T(self.messages.login_button), _type='submit'))

        if settings.remember_me_form:
            ## adds a new input checkbox "remember me for longer"
            if settings.formstyle != 'bootstrap':
                addrow(form, XML("&nbsp;"),
                       DIV(XML("&nbsp;"),
                           INPUT(_type='checkbox',
                                 _class='checkbox',
                                 _id="auth_user_remember",
                                     _name="remember",
                                 ),
                           XML("&nbsp;&nbsp;"),
                           LABEL(
                           self.messages.label_remember_me,
                           _for="auth_user_remember",
                           )), "",
                       settings.formstyle,
                       'auth_user_remember__row')
            elif settings.formstyle == 'bootstrap':
                addrow(form,
                       "",
                       LABEL(
                           INPUT(_type='checkbox',
                                 _id="auth_user_remember",
                                 _name="remember"),
                           self.messages.label_remember_me,
                           _class="checkbox"),
                       "",
                       settings.formstyle,
                       'auth_user_remember__row')

        return form

    def social_login(self, next=DEFAULT):
        self.navbar = lambda **x: ''

        return self.login_form()
        # return current.response.render('plugin_social_auth/login.html')

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
    auth.login_user(user)
    session.auth.expiration = \
        current.request.vars.get('remember', False) and \
        auth.settings.long_expiration or \
        auth.settings.expiration
    session.auth.remember = 'remember' in current.request.vars
    auth.log_event(auth.messages['login_log'], user)
    session.flash = auth.messages.logged_in
