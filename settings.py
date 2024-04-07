from os import environ

SESSION_CONFIGS = [
    dict(
        name='animalfeatures',
        app_sequence=['animalfeatures'],
        num_demo_participants=1,
        condition=None,
    ),
    dict(
        name='animalfeatures_species_recognition',
        app_sequence=['animalfeatures'],
        num_demo_participants=1,
        condition='species_recognition',
    ),
    dict(
        name='animalfeatures_narrative',
        app_sequence=['animalfeatures'],
        num_demo_participants=1,
        condition='narrative',
    ),
    dict(
        name='animalfeatures_aesthetic',
        app_sequence=['animalfeatures'],
        num_demo_participants=1,
        condition='aesthetic',
    ),
]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=0.00, participation_fee=0.00, doc=""
)

PARTICIPANT_FIELDS: list[str] = ['condition', 'stim_order']
SESSION_FIELDS: list[str] = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = '9162952938811'

DEBUG = True