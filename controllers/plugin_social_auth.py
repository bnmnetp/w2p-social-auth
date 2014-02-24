from plugin_social_auth.utils import strategy, get_current_user, login_user

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
    try:
        return do_complete(current.strategy,
                           login=lambda strat, user: login_user(user.row),
                           user=get_current_user())
    except Exception as e:
        #FIXME: For some reason I cannot create except only for SocialAuthBaseException or subclasses.
        # Those exception classes are not being resolved. Also instanceof() is not working.
        # Ideally I want to catch only SocialAuth Exceptions.
        if isinstance(e, HTTP):
            raise
        else:
            session.flash = e.message
            redirect(session.next)


