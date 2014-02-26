from plugin_social_auth.utils import strategy, get_current_user, login_user, process_exception
from social.actions import do_auth, do_complete

@strategy(URL('plugin_social_auth', 'complete'))
def auth_():

    # Store "remember me" value in session
    current.strategy.session_set('remember', current.request.vars.get('remember', False))

    if 'social_identifier' in request.vars:
        redirect(request.vars.social_identifier)
        return

    return do_auth(current.strategy)

@strategy(URL('plugin_social_auth', 'complete'))
def complete():
    try:
        return do_complete(current.strategy,
                           login=lambda strat, user: login_user(user.row),
                           user=get_current_user())
    except Exception as e:
        process_exception(e)


