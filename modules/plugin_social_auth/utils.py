import logging
from plugin_social_auth.social.strategies.utils import get_strategy
from plugin_social_auth.social.utils import setting_name
from plugin_social_auth.social.backends.utils import load_backends
from plugin_social_auth.social.exceptions import SocialAuthBaseException
from plugin_social_auth.social.actions import do_disconnect, do_auth
from plugin_social_auth.models import UserSocialAuth
from models import User
from functools import wraps
from gluon.html import *
from gluon.http import HTTP, redirect
from gluon.globals import current
from gluon.tools import Auth
from gluon.validators import IS_URL
from urlparse import urlparse

def needs_login(f):
    def wrapper(*args):
        selv = args[0]
        r = selv.environment.request
        if not selv.is_logged_in():
            nextt = URL(r=r, args=r.args)
            redirect(URL(args=['login'], vars={'_next': nextt}),
                     client_side=selv.settings.client_side)
        return f(*args)
    return wrapper

DEFAULT = lambda: None
class SocialAuth(Auth):
    """
    Subclass of Auth for authentication using python-social-auth.

    Includes:

    - registration and profile
    - login and logout
    - manage social account associations
    - confirmation for new accounts

    Authentication Example:

        auth=SocialAuth(db)

        # Enable the "username" field
        auth.define_tables(username=True)

        # Disable certain auth actions unless you're also using web2py account registration
        auth.settings.actions_disabled = ['register', 'change_password', 'request_reset_password']

        # Redirect to the same page after logout
        auth.settings.logout_next = URL(args=request.args,
                                        vars=request.get_vars)

    exposes:

    - http://.../{application}/{controller}/{function}/login
    - http://.../{application}/{controller}/{function}/logout
    - http://.../{application}/{controller}/{function}/profile
    - http://.../{application}/{controller}/{function}/associations

    # Used internally by auth pipeline
    - http://.../{application}/{controller}/{function}/confirm

    Other options:

        Change new account confirm message:

        auth.messages.confirm = "Are you sure you want to create a new account"
    """

    def __init__(self, environment):
        Auth.__init__(self, environment, db=None, controller='plugin_social_auth')
        self.messages.update(confirm = self._default_confirm_message)

    @staticmethod
    def get_backends():
        return load_backends(current.plugin_social_auth.plugin.SOCIAL_AUTH_AUTHENTICATION_BACKENDS)

    @staticmethod
    def get_providers():
        return current.plugin_social_auth.plugin.SOCIAL_AUTH_PROVIDERS

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

    def dropdown_form(self, backends=None, next=None, button_label=None):
        return FORM((self.remember_me_form() if self.remember_me_form else ''),
                    INPUT(_type='hidden', _name='next',_value=next or self.get_vars_next()),
                    INPUT(_type='hidden', _id='assertion', _name='assertion'), # Used for Mozilla Persona
                    DIV(SocialAuth.dropdown(backends),
                        DIV(INPUT(_value=button_label or current.plugin_social_auth.T(self.messages.login_button), _type='submit'))),
                    _id='social_dropdown_form')

    def openid_form(self, next=None):
        return FORM((self.remember_me_form() if self.remember_me_form else ''),
                    INPUT(_type="hidden", _name="backend", _value="openid"),
                    INPUT(_type="hidden", _name="next", _value=next or self.get_vars_next()),
                    DIV(DIV(DIV(INPUT(_id="openid_identifier",
                                      _name="openid_identifier",
                                      _placeholder="Or, manually enter your OpenId",
                                      _type="text",
                                      requires=[IS_URL(), IS_ALLOWED_OPENID()])),
                            DIV(INPUT(_type="submit", _value="Submit"))),
                        _id="openid_identifier_area"),
                    _id="social_openid_form")

    def disconnect_form(self, next=None, usas=None, providers=None):
        usas = usas or UserSocialAuth.get_social_auth_for_user(get_current_user())
        usas_no_openid = [usa for usa in usas if usa.provider != 'openid']
        providers = providers or SocialAuth.get_providers()

        # Add list with currently connected accounts
        form = FORM(SELECT(_name='association_id', _size=5),
                    INPUT(_type="hidden", _name="next", _value=next),
                    DIV(INPUT(_value='Disconnect', _type='submit') if len(usas) > 1 else ''))

        for usa in usas_no_openid:
            form[0].append(OPTION(providers[usa.provider], _value=usa.id))

        i = 0
        for usa in [x for x in usas if x.provider == 'openid']:
            i += 1
            form[0].append(OPTION('OpenID [%s]' % urlparse(usa.uid).hostname, _value=usa.id))

        form[0][0]['_selected'] = 'selected'

        return form

    def _default_confirm_message(self, backend_name):
        T = current.plugin_social_auth.T
        backend = {'backend': backend_name}
        return DIV(P(H3(T('Are you a new user?'))),
                P(T('Please click "Register" to create an new account using %(backend)s' % backend)),
                P(H3(T('Are you an existing user?'))),
                P(T('Are you sure you want to create a new account? If you want to add %(backend)s login to your existing account:' % backend),
                    OL(LI(T('Click "Cancel"')),
                       LI(T('Login using a previously used social account')),
                       LI(T('Add %(backend)s to your logins' % backend))),
                    T('If you click "Register", a new account will be created with %(backend)s as login' % backend)),
                _class="alert")

    def confirm_form(self, backend_name):
        T = current.plugin_social_auth.T
        msg = self.messages.confirm
        return FORM(msg(backend_name) if callable(msg) else msg,
                    INPUT(_type="hidden", _name="next", _value=self.get_vars_next()),
                    DIV(INPUT(_value=T('Register'), _type='submit'),
                        A(INPUT(_type='button' ,_value=T('Cancel')), _href=URL(f='user'))))

    def confirm(self):
        # Hide auth navbar
        self.navbar = lambda **x: ''

        form = self.confirm_form(SocialAuth.get_providers()[current.request.vars.backend])

        if form.process().accepted:
            # Get vars back from session and delete them
            varz = current.plugin_social_auth.s.pop('confirm', {})

            return redirect(URL(f='complete', args=['confirmed'], vars=varz))

        return current.response.render(dict(form=form))

    def social_login(self, next=DEFAULT):
        # Hide auth navbar
        self.navbar = lambda **x: ''

        form1 = self.dropdown_form()
        form2 = self.openid_form()

        if form1.process(formname='form_one').accepted or form2.process(formname='form_two').accepted:
            return _auth()

        return dict(form=DIV(H4(current.plugin_social_auth.T('Choose your provider:')),
                             form1,
                             P(EM(current.plugin_social_auth.T('Or manually enter your OpenId:'))),
                             form2),
                    enable_persona=current.plugin_social_auth.plugin.SOCIAL_AUTH_ENABLE_PERSONA)

    @needs_login
    def associations(self):
        """Shows form to manage social account associations."""
        nextt = URL(args=['associations'])

        usas = UserSocialAuth.get_social_auth_for_user(get_current_user())
        providers = SocialAuth.get_providers()

        form1 = self.disconnect_form(usas=usas, providers=providers, next=nextt)

        backends = [backend for backend in SocialAuth.get_backends().keys() if
                    backend not in [x.provider for x in usas] and backend in providers]

        form2 = self.dropdown_form(next=nextt, button_label=current.plugin_social_auth.T("Connect"),
                                   backends=backends)

        form3 = self.openid_form(next=nextt)

        if form1.process(formname='form_one').accepted:
            return _disconnect()
        if form2.process(formname='form_two').accepted or form3.process(formname='form_three').accepted:
            return _auth()

        form = DIV(FIELDSET(LEGEND(current.plugin_social_auth.T('Your logons')),
                            form1),
                   FIELDSET(LEGEND(current.plugin_social_auth.T('Add new logon')),
                            form2,
                            P(EM(current.plugin_social_auth.T('Or manually enter your OpenId:'))),
                            form3))

        return dict(form=form, enable_persona=current.plugin_social_auth.plugin.SOCIAL_AUTH_ENABLE_PERSONA)

    @needs_login
    def profile(self, *args, **kwargs):
        return super(SocialAuth, self).profile(*args, **kwargs)

    def navbar(self, prefix='Welcome', action=None,
               separators=(' [ ', ' | ', ' ] '), user_identifier=DEFAULT,
               referrer_actions=DEFAULT, mode='default'):

        def make_user_id(user):
            first_name = user.get('first_name', '')
            if first_name != '':
                return first_name
            username = user.get('username', '')
            if username != '':
                return username
            email = user.get('email', '')
            if email != '':
                return email.split('@', 1)[0]

        return super(SocialAuth, self).navbar(prefix=prefix, action=action, separators=separators,
                                              user_identifier=make_user_id, mode=mode)

    def __call__(self):
        request = self.environment.request
        args = request.args
        if not args:
            redirect(URL(r=request, args='login'))
        if args[0] == 'login':
            return self.social_login()
        if args[0] == 'logout':
            return self.logout()
        if args[0] == 'confirm':
            return self.confirm()
        elif args[0] in ['logout', 'associations', 'confirm', 'profile']:
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

class IS_ALLOWED_OPENID(object):
    """
    Validate if the supplied OpenID url is for an allowed provider.
    Background:

    Google OpenID should not be used with manual OpenID entry because
    Google may use different ID's for different domains so it's not guaranteed to
    always stay the same. If you want to use Google OpenId, use:
    social.backends.google.GoogleOpenId (will use email as ID)

    http://blog.stackoverflow.com/2010/04/openid-one-year-later/
    http://blog.stackoverflow.com/2009/04/googles-openids-are-unique-per-domain/
    """
    def __init__(self, error_message='This OpenID provider is not allowed.'):
        self.e = error_message
    def __call__(self, value):
        host = urlparse(value).hostname
        error = None
        if host in current.plugin_social_auth.plugin.SOCIAL_AUTH_DISALLOWED_OPENID_HOSTS:
            error = self.e
        return value, error

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
            r = current.request
            uri = redirect_uri
            backend = r.vars.backend
            association_id = r.vars.association_id

            if association_id and not backend:
                usa = UserSocialAuth.get_social_auth_for_user(association_id=association_id)
                if usa and len(usa) > 0:
                    backend = usa[0].provider

            current.strategy = load_strategy(request=r,
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

@strategy(URL(args=['associations']))
def _disconnect():
    """Disconnects given backend from current logged in user."""
    def on_disconnected(backend):
        providers = current.plugin_social_auth.plugin.SOCIAL_AUTH_PROVIDERS
        display_name = backend in providers and providers[backend]

        current.plugin_social_auth.session.flash = \
            '%s %s' % (current.plugin_social_auth.T('Removed logon: '), display_name or backend)

    try:
        return do_disconnect(current.strategy, get_current_user(),
                             association_id=current.request.vars.association_id,
                             on_disconnected=on_disconnected)
    except Exception as e:
        process_exception(e)

@strategy(URL('plugin_social_auth', 'complete'))
def _auth():
    r = current.request

    # Store "remember me" value in session
    current.strategy.session_set('remember', r.vars.get('remember', False))

    if r.vars.backend == 'persona':
        # Mozilla Persona
        if r.vars.assertion == '': del r.vars.assertion
        redirect(URL(f='complete', args=['persona'], vars=r.vars))
    else:
        try:
            return do_auth(current.strategy)
        except Exception as e:
            process_exception(e)

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