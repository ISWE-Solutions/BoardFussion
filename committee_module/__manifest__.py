# -*- coding: utf-8 -*-
{
    'name': "committee_module",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'hr_skills', 'hr_skills_survey', 'documents', 'hr_contract_salary', 'hr_gamification',
                'hr_appraisal', 'hr_contract', 'hr_payroll', "product","project","account","sale","web","website_sale", "website_partner", "task_overdue_email_odoo"],

    "data": [
        # security/ir.model.access.csv",
        "data/tag_data.xml",
        # data/hr_appraisal_templates_inherit.xml",
        # "views/title.xml",
        "views/member_view.xml",
        "views/views.xml",
        "views/email.xml",
        "views/templates.xml",
        "views/department_views_inherit.xml",
        "views/employee_views_inherit.xml",
        "views/employee_views_inherit_public.xml",
        "views/job_views_inherit.xml",
        "views/hr_users_views_inherit.xml",
        "views/mail_activity_plan_views_inheirt.xml",
        "views/appraisal_evaluation_views_inherit.xml",
        "views/contract_views_inherit.xml",
        "views/hr_payroll_view_inherit.xml",
        "views/projects.xml",
        "views/config.xml",
        "views/survey.xml",
        # views/web_UserMenu_views.xml",
        "views/product_document_views.xml",
        # "views/hr_employee_delete_wizard_form_inherit.xml",
    ],
    'installable': True,
    'application': False,
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    "assets": {
        "web.assets_backend": [
            "committee_module/static/src/components/**/*.js",
            "committee_module/static/src/components/**/*.xml",
            "committee_module/static/src/components/**/*.scss",
            "committee_module/static/src/js/favicon.js",
            "committee_module/static/src/js/title.js",
        ],
    },
    'license': "LGPL-3",
}
