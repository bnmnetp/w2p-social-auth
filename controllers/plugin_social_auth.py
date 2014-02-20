from plugin_social_auth.utils import strategy, get_current_user

@strategy(URL('plugin_social_auth', 'complete'))
def auth_():
    from social.actions import do_auth
    if 'social_identifier' in request.vars:
        redirect(request.vars.social_identifier)
        return

    return do_auth(current.strategy)

@strategy(URL('plugin_social_auth', 'complete'))
def complete():
    from social.actions import do_complete
    return do_complete(current.strategy,
                       login=lambda strat, user: auth.login_user(user.row),
                       user=get_current_user())
