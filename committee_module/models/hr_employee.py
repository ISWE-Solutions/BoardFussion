from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    committees_ids = fields.Many2many('hr.department', string="Committees")
    job_id = fields.Many2one('hr.job', string="Title")
    registration_number = fields.Char(string="Registration Number of the Member")
    next_appraisal_date = fields.Date(string="Next Evaluation Date")

    employee_type = fields.Selection([
        ('member','Member'),
        ('employee', 'Employee'),
        ('student', 'Student'),
        ('trainee', 'Trainee'),
        ('contractor', 'Contractor'),
        ('freelance', 'Freelancer'),
    ], string='Employee Type', default='member', required=True, groups="hr.group_hr_user",
        help="The member type. Although the primary purpose may seem to categorize members, this field has also an impact in the Contract History. Only Member type is supposed to be under contract and will have a Contract History.")

    member_type = fields.Selection([
        ('board_member', 'Board Member'),
        ('employee', 'Member'),
        ('senior_management', 'Senior Management'),
        ('hod', 'Head of Department'),
        ('secretariate', 'Secretariate'),
    ], string='Member Type', default='board_member', required=True)

    @api.onchange("committees_ids","department_id")
    def _onchange_committee(self):

        if self.committees_ids:
           self.department_id = self.committees_ids[0].id

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'
    _description = 'Members'

    committees_ids = fields.Many2many(
        'hr.department',
        'hr_department_hr_employee_public_rel',  # Relation table name
        'employee_id',  # Field name in relation table for hr.employee.public
        'department_id',  # Field name in relation table for hr.department
        string="Committees"
    )


    job_id = fields.Many2one('hr.job', string="Title")
    department_id = fields.Many2one('hr.department', string="Committee")
    parent_id = fields.Many2one(invisible="True")
    coach_id = fields.Many2one(invisible="True")
    registration_number = fields.Char(string="Registration Number of the Member")
    next_appraisal_date = fields.Date(string="Next Evaluation Date")
    first_contract_date = fields.Date(string="First Tenure Date")
    name = fields.Char(string="Members Name")


    employee_type = fields.Selection([
        ('member','Member'),
        ('employee', 'Employee'),
        ('student', 'Student'),
        ('trainee', 'Trainee'),
        ('contractor', 'Contractor'),
        ('freelance', 'Freelancer'),
    ], string='Employee Type', default='member', required=True, groups="hr.group_hr_user",
        help="The member type. Although the primary purpose may seem to categorize members, this field has also an impact in the Contract History. Only Member type is supposed to be under contract and will have a Contract History.")

    member_type = fields.Selection([
        ('board_member', 'Board Member'),
        ('employee', 'Member'),
        ('senior_management', 'Senior Management'),
        ('hod', 'Head of Department'),
        ('secretariate', 'Secretariate'),
    ], string='Member Type', default='board_member', required=True)

    @api.onchange("committees_ids","department_id")
    def _onchange_committee(self):

        if self.committees_ids:
           self.department_id = self.committees_ids[0].id


class HrContract(models.Model):
    _inherit = 'hr.contract'

    default_contract_id = fields.Many2one(string='Tenure Template')
    sign_template_id = fields.Many2one(string='New Tenure Document Template')
    contract_update_template_id = fields.Many2one(string='Tenure Update Document Template')
    hr_responsible_id = fields.Many2one(string='Responsible')


class HrTimesheet(models.Model):
    _inherit = 'account.analytic.line'

    employee_id = fields.Many2one(string='Member')
    project_id = fields.Many2one(string='Action Point')


class Onboarding(models.Model):
    _inherit = 'mail.activity.plan.template'

    employee_role_id = fields.Many2one(string='Member Role')
