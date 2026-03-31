{
    'name': 'Eisenhower Matrix',
    'version': '19.0.1.0.0',
    'summary': 'Prioritize chatter activities with an Eisenhower matrix dashboard',
    'description': """
Prioritize Odoo chatter activities with an Eisenhower matrix workflow.

Main features:
- Personal and team activity overview
- 2x2 Eisenhower matrix dashboard
- Drag and drop between quadrants
- Priority stars and quadrant ordering
- List, kanban, pivot and graph analysis views
    """,
    'author': 'Lean Digital Studio',
    'website': 'https://www.leandigitalstudio.it',
    'support': 'info@leandigitalstudio.it',
    'license': 'LGPL-3',
    'category': 'Productivity/Discuss',
    'price': 29.99,
    'currency': 'EUR',
    'depends': ['mail', 'hr'],
    'data': [
        'views/mail_activity_views.xml',
        'views/eisenhower_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'eisenhower_activity_matrix/static/src/js/eisenhower_matrix.js',
            'eisenhower_activity_matrix/static/src/xml/eisenhower_matrix.xml',
            'eisenhower_activity_matrix/static/src/scss/eisenhower_matrix.scss',
        ],
    },
    'images': [
        'static/description/banner.png',
        'static/description/screenshot_01.png',
        'static/description/screenshot_02.png',
        'static/description/screenshot_03.png',
    ],
    'installable': True,
    'application': True,
}
