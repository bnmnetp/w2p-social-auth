from plugin_social_auth.utils import strategy, get_current_user, login_user, process_exception, SocialAuth
from plugin_social_auth.social.actions import do_auth, do_complete, do_disconnect

@strategy(URL('plugin_social_auth', 'complete'))
def auth_():

    # Store "remember me" value in session
    current.strategy.session_set('remember', current.request.vars.get('remember', False))

    try:
        return do_auth(current.strategy)
    except Exception as e:
        process_exception(e)


@strategy(URL('plugin_social_auth', 'complete'))
def complete():
    try:
        return do_complete(current.strategy,
                           login=lambda strat, user: login_user(user.row),
                           user=get_current_user())
    except Exception as e:
        process_exception(e)

@auth.requires_login()
@strategy(URL('plugin_social_auth', 'disconnect'))
def disconnect():
    """Disconnects given backend from current logged in user."""
    association_id = request.vars.association_id

    def on_disconnected(backend):
        session.flash = '%s %s' % (T('Removed logon: '), backend)

    try:
        return do_disconnect(current.strategy, get_current_user(), association_id, on_disconnected=on_disconnected)
    except Exception as e:
        process_exception(e)

@auth.requires_login()
def associations():
    """Shows form to manage social account associat
    response.title = T('Manage logins')ions."""
    return dict(form=auth.manage_form())

def user():
    return auth()



