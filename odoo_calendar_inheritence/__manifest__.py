# -*- coding: utf-8 -*-
{
    'name': "odoo_calendar_inheritence",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "Softbox",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'project',
                'calendar',
                'mail',
                'rating',
                'portal',
                'hr',
                'survey',
                'product',
                'qxm_product_pdf_annotation_tool',
                'knowledge',
                'website_sale',
                "appointment",
                "web"
                ],

    # always loaded

    'data': [
        'security/res_groups.xml',
        'security/custom_calendar_access_rights.xml',
        'security/ir.model.access.csv',
        'data/meeting_email_template.xml',
        'data/product_category.xml',
        'data/knowledge_article_sequence.xml',
        # 'data/products_cron.xml',
        'views/calendar_event_product_line_view.xml',
        'views/attendees_lines_view.xml',
        'views/views.xml',
        'views/templates.xml',
        # 'views/pdf_merger_server_action.xml',
        'views/product_document_views.xml',
        'views/custom_calendar_view.xml',
        'views/knowledge_article_views.xml',
        'views/project_task_view.xml',
        'views/calender_event_view.xml',
        'views/appointments_view.xml',
        # 'views/employee.xml',
    ],

    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
