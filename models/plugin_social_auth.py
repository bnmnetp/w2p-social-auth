from json import loads, dumps

db.define_table('plugin_social_auth_user',
                Field('provider', 'string', notnull=True, writable=False),
                Field('oauth_uid', 'string', notnull=True, writable=False, length=255),
                Field('extra_data', 'text', writable=False, requires=IS_JSON),
                Field('oauth_user', 'reference auth_user', writable=False, notnull=True))

db.plugin_social_auth_user.extra_data.filter_in = lambda obj, dumps=dumps: dumps(obj)
db.plugin_social_auth_user.extra_data.filter_out = lambda txt, loads=loads: loads(txt) if txt else None

db.define_table('plugin_social_auth_nonce',
                Field('server_url', 'string', notnull=True, readable=False, writable=False, length=255),
                Field('timestamp', 'integer', notnull=True, readable=False, writable=False),
                Field('salt', 'string', notnull=True, readable=False, writable=False, length=40))

db.define_table('plugin_social_auth_association',
                Field('server_url', 'string', notnull=True, readable=False, writable=False, length=255),
                Field('handle', 'string', notnull=True, readable=False, writable=False, length=255),
                Field('secret', 'string', notnull=True, readable=False, writable=False, length=255),
                Field('issued', 'integer', notnull=True, readable=False, writable=False),
                Field('lifetime', 'integer', notnull=True, readable=False, writable=False),
                Field('assoc_type', 'string', notnull=True, readable=False, writable=False, length=64))

_defaults = {'SOCIAL_AUTH_USER_MODEL': 'User',
             'SOCIAL_AUTH_USER_FIELDS': ['first_name', 'last_name', 'username', 'email']}

_plugins = PluginManager('social_auth', **_defaults)

# expose globals to plugin_social_auth
current.plugin_social_auth = Storage()
current.plugin_social_auth.session = session
current.plugin_social_auth.auth = auth
current.plugin_social_auth.db = db
current.plugin_social_auth.plugin = _plugins.social_auth

