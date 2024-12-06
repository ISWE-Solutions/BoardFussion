from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    name = fields.Char(string="Member Name", related='resource_id.name', store=True, readonly=False, tracking=True)
    committees_ids = fields.Many2many('hr.department', string="Committees")
    job_id = fields.Many2one('hr.job', string="Title")
    registration_number = fields.Char(string="Registration Number of the Member")
    next_appraisal_date = fields.Date(string="Next Evaluation Date")

    member_type = fields.Selection([
        ('board_member', 'Board Member'),
        ('employee', 'Member'),
        ('senior_management', 'Senior Management'),
        ('hod', 'Head of Department'),
        ('secretariate', 'Secretariate'),
    ], string='Member Type', default='board_member', required=True)

    @api.onchange("committees_ids", "department_id")
    def _onchange_committee(self):

        if self.committees_ids:
            self.department_id = self.committees_ids[0].id

    def toggle_active(self):
        super(HrEmployee, self).toggle_active()  # Call the parent method

        for employee in self:
            if not employee.active:
                print(f"Archiving employee: {employee.name} (ID: {employee.id})")

                # Get the associated user
                user = self.env['res.users'].search([('id', '=', employee.user_id.id)])

                # Check if the user is active and archive the user first
                if user and user.active:
                    print(f"Archiving associated user: {user.login}")
                    user.write({'active': False})  # Deactivate the user

                # Archive partners where employee_ids contain this employee, and only consider active partners
                partners = self.env['res.partner'].search([
                    ('employee_ids', '=', employee.id),
                    ('active', '=', True)  # Only consider active partners for archiving
                ])
                if partners:
                    print(
                        f"Found active partners related to employee {employee.name}: {[partner.name for partner in partners]}")
                    partners.write({'active': False})  # Deactivate partners
                    print(f"Archived {len(partners)} partner(s) related to employee {employee.name}")
                else:
                    print(f"No active partners found related to employee {employee.name}")

            else:
                print(f"Activating employee: {employee.name} (ID: {employee.id})")

                # Unarchive partners where employee_ids contain this employee, and only consider archived partners
                partners = self.env['res.partner'].search([
                    ('employee_ids', '=', employee.id),
                    ('active', '=', False)  # Only consider archived partners for unarchiving
                ])
                if partners:
                    print(
                        f"Found archived partners related to employee {employee.name}: {[partner.name for partner in partners]}")
                    partners.write({'active': True})  # Reactivate partners
                    print(f"Unarchived {len(partners)} partner(s) related to employee {employee.name}")
                else:
                    print(f"No archived partners found related to employee {employee.name} for unarchiving.")

                # Unarchive the user linked to this employee
                user = self.env['res.users'].search(
                    [('id', '=', employee.user_id.id), ('active', '=', False)])  # Search for archived user
                if user:
                    print(f"Found archived user related to employee {employee.name}: {user.login}")
                    user.write({'active': True})  # Reactivate the user
                    print(f"Unarchived user related to employee {employee.name}: {user.login}")
                else:
                    print(f"No archived user found related to employee {employee.name} for unarchiving.")

                # Debugging: Check the state of employee_ids
                employee_partners = self.env['res.partner'].search([
                    ('employee_ids', '=', employee.id),
                    ('active', '=', False)  # Check currently linked archived partners
                ])
                if employee_partners:
                    print(
                        f"Currently linked archived partners to employee {employee.name}: {[partner.name for partner in employee_partners]}")
                else:
                    print(f"No archived partners currently linked to employee {employee.name} in employee_ids.")


    def unlink(self):
        for employee in self:
            if employee.active:
                print(f"Archiving employee: {employee.name} (ID: {employee.id})")

                # Get the associated user
                user = self.env['res.users'].search([('id', '=', employee.user_id.id)])

                # Check if the user is active and archive the user first
                if user and user.active:
                    print(f"Archiving associated user: {user.login}")
                    user.write({'active': False})  # Deactivate the user

                # Archive partners where employee_ids contain this employee, and only consider active partners
                partners = self.env['res.partner'].search([
                    ('employee_ids', '=', employee.id),
                    ('active', '=', True)  # Only consider active partners for archiving
                ])
                if partners:
                    print(f"Found active partners related to employee {employee.name}: {[partner.name for partner in partners]}")
                    partners.write({'active': False})  # Deactivate partners
                    print(f"Archived {len(partners)} partner(s) related to employee {employee.name}")
                else:
                    print(f"No active partners found related to employee {employee.name}")

        # Call the super method to actually unlink the employees after archiving related records
        return super(HrEmployee, self).unlink()


    @api.model_create_multi
    def create(self, vals_list):
        # Suppress automatic "Employee created" chatter message
        self = self.with_context(mail_create_nolog=True)

        # Call the super create method to create the employees with all the default logic
        employees = super(HrEmployee, self).create(vals_list)

        # Add your custom logic to log "Member created" instead
        for employee in employees:
            employee.message_post(body="Member created")

        # Return the created employees
        return employees


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
    department_id = fields.Many2one('hr.department', string="Committee", default=False)
    parent_id = fields.Many2one(invisible="True")
    coach_id = fields.Many2one(invisible="True")
    registration_number = fields.Char(string="Registration Number of the Member")
    next_appraisal_date = fields.Date(string="Next Evaluation Date")
    first_contract_date = fields.Date(string="First Tenure Date")
    name = fields.Char(string="Members Name")

    employee_type = fields.Selection([
        ('member', 'Member'),
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

    @api.onchange("committees_ids", "department_id")
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
