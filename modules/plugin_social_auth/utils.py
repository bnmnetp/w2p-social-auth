import logging
from plugin_social_auth.social.strategies.utils import get_strategy
from plugin_social_auth.social.utils import setting_name
from plugin_social_auth.social.backends.utils import load_backends
from plugin_social_auth.social.exceptions import SocialAuthBaseException
from plugin_social_auth.social.pipeline.social_auth import associate_user as assoc_user
from plugin_social_auth.models import UserSocialAuth
from models import User
from functools import wraps
from gluon.html import *
from gluon.http import HTTP, redirect
from gluon.globals import current
from gluon.tools import Auth
from gluon.validators import IS_URL

DEFAULT = lambda: None
class SocialAuth(Auth):
    def __init__(self, environment):
        Auth.__init__(self, environment, db=None, controller='plugin_social_auth')

    @staticmethod
    def get_backends():
        return load_backends(current.plugin_social_auth.plugin.SOCIAL_AUTH_AUTHENTICATION_BACKENDS)

    @staticmethod
    def get_providers():
        return current.plugin_social_auth.plugin.SOCIAL_AUTH_PROVIDERS

    def manage_form(self):
        div = DIV()

        # Get all social account for current user
        usas = UserSocialAuth.get_social_auth_for_user(get_current_user())

        providers = SocialAuth.get_providers()

        # Add list with currently connected account
        div.append(H4(current.plugin_social_auth.T('Your logons')))
        table = TABLE()
        for usa in usas:
            table.append(TR(TD(providers[usa.provider]),
                            TD(A(current.plugin_social_auth.T("remove"),
                                 _href=URL('plugin_social_auth', 'disconnect',
                                           vars=dict(backend=usa.provider, next=URL()))) if len(usas) > 1 else '')))
        div.append(table)

        # Add dropdown to connect new accounts
        div.append(H4(current.plugin_social_auth.T('Add new logon')))
        backends = [backend for backend in SocialAuth.get_backends().keys() if
                    backend not in [x.provider for x in usas] and backend in providers]
        div.append(self.dropdown_form(remember_me_form=False, next=URL(),
                                      button_label=current.plugin_social_auth.T("Connect"),
                                      backends=backends))

        return div

    @staticmethod
    def login_links():
        """ Returns a list with links for every configured backend.
        Can be used in stead of login_form()
        """
        providers = SocialAuth.get_providers()
        div = DIV()
        for name in sorted(SocialAuth.get_backends().iterkeys()):
            if name in providers:
                div.append(A(providers['name'], _href=URL('plugin_social_auth', 'auth_', vars=dict(backend=name, next=current.request.vars._next))))
                div.append(BR())
        return div

    @staticmethod
    def dropdown(backends):
        providers = SocialAuth.get_providers()
        select = SELECT(_id='backend-select',_name='backend')
        for backend in sorted(backends or SocialAuth.get_backends().keys()):
            if backend in providers:
                option = OPTION(providers[backend], _value=backend)
                select.append(option)
                # Persona required js. Hide it initially (to show it again using js)
                if backend == 'persona':
                    option['_id'] = "persona-option"
                    option['_style'] = "display:none;"

        return select

    def remember_me_form(self):
        return DIV(XML("&nbsp;"),
                   INPUT(_type='checkbox',
                         _class='checkbox',
                         _id="auth_user_remember",
                         _name="remember"),
                   XML("&nbsp;&nbsp;"),
                   LABEL(self.messages.label_remember_me,
                         _for="auth_user_remember",
                         _style="display: inline-block"))

    def dropdown_form(self, remember_me_form=True, backends=None, next=None, button_label=None, action=URL('plugin_social_auth', 'auth_')):
        return FORM((self.remember_me_form() if remember_me_form else ''),
                    INPUT(_type='hidden', _name='next',_value=next or self.get_vars_next()),
                    INPUT(_type='hidden', _id='assertion', _name='assertion'), # Used for Mozilla Persona
                    DIV(SocialAuth.dropdown(backends),
                        DIV(INPUT(_value=button_label or current.plugin_social_auth.T(self.messages.login_button), _type='submit'))),
                    _action=action,
                    _id='social_dropdown_form')

    def openid_form(self, remember_me_form=True):
        return FORM((self.remember_me_form() if remember_me_form else ''),
                    INPUT(_type="hidden", _name="backend", _value="openid"),
                    INPUT(_type="hidden", _name="next", _value=self.get_vars_next()),
                    DIV(DIV(DIV(INPUT(_id="openid_identifier",
                                      _name="openid_identifier",
                                      _placeholder="Or, manually enter your OpenId",
                                      _type="text",
                                      requires=IS_URL())),
                            DIV(INPUT(_type="submit", _value="Submit"))),
                        _id="openid_identifier_area"),
                    _id="social_openid_form")

    def social_login(self, next=DEFAULT):
        # Hide auth navbar
        self.navbar = lambda **x: ''

        form1 = self.dropdown_form()
        form2 = self.openid_form()
        accepted = False
        if form1.process(formname='form_one').accepted:
            accepted = True
        if form2.process(formname='form_two').accepted:
            accepted = True
        if accepted:
            redirect(URL('plugin_social_auth', 'auth_',
                     # Convert post_vars to get_vars for redirect
                     vars={your_key: current.request._vars[your_key] for
                           your_key in ['backend', 'openid_identifier', 'next']}))
        return dict(form1=form1, form2=form2, enable_persona=use_persona())

    def __call__(self):
        request = self.environment.request
        args = request.args
        if not args:
            redirect(URL(r=request, args='login'))
        if args[0] == 'login':
            return self.social_login()
        elif args[0] in ['logout', 'groups', 'profile']:
             return getattr(self, args[0])()
        else:
            raise HTTP(404)

class W2pExceptionHandler(object):
    """Class that handles Social Auth AuthExceptions by providing the user
    with a message, logging an error, and redirecting to some next location.

    By default, the exception message itself is sent to the user using a flash and
    they are redirected to the location specified in the SOCIAL_AUTH_LOGIN_ERROR_URL
    setting or to the url stored in the 'next' var.
    """
    def process_exception(self, exception):
        self.strategy = current.strategy
        if self.strategy is None or self.raise_exception():
            raise

        #FIXME: workaround for issue:
        # https://code.google.com/p/w2p-social-auth/issues/detail?id=1
        def is_social_auth_exception(ex):
            return ex.__class__.__module__ in('social.exceptions', SocialAuthBaseException.__module__)

        if is_social_auth_exception(exception):
            backend_name = self.strategy.backend.name
            message = exception.message

            logging.error("[social_auth] backend: %s | message: %s" % (backend_name, message))

            current.newsranx.session.flash = message
            redirect(self.get_redirect_uri())
        else:
            raise

    def raise_exception(self):
        return self.strategy.setting('RAISE_EXCEPTIONS')

    def get_redirect_uri(self):
        return self.strategy.setting('LOGIN_ERROR_URL') or current.strategy.session_get('next')

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

def module_member(name):
    mod, member = name.rsplit('.', 1)
    subs = mod.split('.')
    if len(subs) > 1:
        fromlist = '.'.join(subs[1:])
        module = __import__(mod, fromlist=fromlist)
    else:
        module = __import__(mod)

    return getattr(module, member)

def get_exception_handler(strategy):
    setting = strategy.setting('EXCEPTION_HANDLER')
    handler = None
    if setting:
        handler = module_member(setting)()
    return handler

def process_exception(exception):
    strategy = current.strategy
    if strategy:
        handler = get_exception_handler(strategy)
        if handler:
            handler.process_exception(exception)
        else:
            raise

def use_persona():
    return current.plugin_social_auth.plugin.SOCIAL_AUTH_ENABLE_PERSONA

# Custom  pipeline functions
def disconnect(strategy, entries, user_storage, on_disconnected=None,  *args, **kwargs):
    for entry in entries:
        user_storage.disconnect(entry, on_disconnected)

def associate_user(strategy, uid, user=None, social=None, *args, **kwargs):
    assoc = assoc_user(strategy, uid, user=user, social=social, *args, **kwargs)
    if assoc:
        current.plugin_social_auth.session.flash = '%s %s' % \
                (current.plugin_social_auth.T('Added logon: '), strategy.backend.name)
    return assoc