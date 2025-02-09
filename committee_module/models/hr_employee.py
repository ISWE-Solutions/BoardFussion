from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)
class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    name = fields.Char(string="Member Name", related='resource_id.name', store=True, readonly=False, tracking=True)
    committees_ids = fields.Many2many('hr.department', string="Committees")
    job_id = fields.Many2one('hr.job', string="Title")
    registration_number = fields.Char(string="Registration Number of the Member")
    next_appraisal_date = fields.Date(string="Next Evaluation Date")
    partner_id = fields.Many2one('res.partner', string="Partner")

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

    def _inverse_work_contact_details(self):
        # If we are already syncing, don't continue.
        if self.env.context.get('skip_inverse_sync'):
            return
        for employee in self:
            if employee.work_contact_id:
                vals = {
                    'name': employee.name,
                    'email': employee.work_email,
                    'phone': employee.work_phone,
                    'mobile': employee.mobile_phone,
                    # Add other fields as needed.
                }
                # When writing to the partner, pass two flags:
                # - skip_employee_update: so that partner.write() doesn't trigger employee update.
                # - skip_inverse_sync: so that if the inverse is triggered again, it immediately returns.
                employee.work_contact_id.sudo().with_context(
                    skip_employee_update=True,
                    skip_inverse_sync=True
                ).write(vals)

    def _create_work_contacts(self):
        """Create a work contact (res.partner) only if no partner with the same work_email exists."""
        for employee in self:
            # Skip employees that already have a work contact assigned
            if employee.work_contact_id:
                continue

            partner = False
            if employee.work_email:
                # Search for an existing partner with the same work email
                partner = self.env['res.partner'].search([('email', '=', employee.work_email)], limit=1)

            if not partner:
                # No existing partner found; create a new one
                partner = self.env['res.partner'].create({
                    'name': employee.name,
                    'email': employee.work_email,
                    'mobile': employee.mobile_phone,
                    'image_1920': employee.image_1920,
                    'company_id': employee.company_id.id,
                })
                _logger.info("Created new partner %s for employee %s", partner.id, employee.id)
            else:
                _logger.info("Found existing partner %s for employee %s", partner.id, employee.id)

            # Assign the found or newly created partner as the work contact
            employee.work_contact_id = partner

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            work_email = vals.get('work_email')
            if work_email:
                existing_partner = self.env['res.partner'].search(
                    [('email', '=', work_email)],
                    limit=1
                )
                if existing_partner:
                    vals['work_contact_id'] = existing_partner.id
                    _logger.info(
                        "Linked existing partner %s to employee.",
                        existing_partner.id
                    )
        # Create employees without triggering partner creation
        employees = super().create(vals_list)
        employees._create_work_contacts()
        return employees

    def write(self, vals):
        # Avoid recursion when updating partner from employee and vice versa
        if self.env.context.get('skip_partner_update', False):
            return super(HrEmployee, self).write(vals)

        # === Original Functionality Before the Write ===
        # 1. Handle work_contact_id updates: update bank accounts and messaging subscriptions
        if 'work_contact_id' in vals:
            # Get bank account ids from provided vals or from the employee record
            account_ids = vals.get('bank_account_id') or self.bank_account_id.ids
            if account_ids:
                bank_accounts = self.env['res.partner.bank'].sudo().browse(account_ids)
                for bank_account in bank_accounts:
                    if vals['work_contact_id'] != bank_account.partner_id.id:
                        if bank_account.allow_out_payment:
                            bank_account.allow_out_payment = False
                        if vals['work_contact_id']:
                            bank_account.partner_id = vals['work_contact_id']
            self.message_unsubscribe(self.work_contact_id.ids)
            if vals.get('work_contact_id'):
                self._message_subscribe([vals['work_contact_id']])

        # 2. Sync profile picture from user if user_id is updated
        if 'user_id' in vals:
            user = self.env['res.users'].browse(vals['user_id'])
            # The flag below ensures that if all selected employees already have an image,
            # the sync won’t overwrite it (adjust as needed for your use case).
            sync_vals = self._sync_user(user, bool(all(emp.image_1920 for emp in self)))
            vals.update(sync_vals)

        # 3. If the work permit expiration date is changed, reset the scheduled activity flag
        if 'work_permit_expiration_date' in vals:
            vals['work_permit_scheduled_activity'] = False

        # === Perform the Write on the Employee Record ===
        res = super(HrEmployee, self).write(vals)

        # 4. If department or user changed, subscribe the employee to the channels associated with the department
        if vals.get('department_id') or vals.get('user_id'):
            department_id = vals.get('department_id') or self[:1].department_id.id
            self.env['discuss.channel'].sudo().search([
                ('subscription_department_ids', 'in', department_id)
            ])._subscribe_users_automatically()

        # 5. Post additional departure information if provided
        if vals.get('departure_description'):
            self.message_post(body=_(
                'Additional Information: \n %(description)s',
                description=vals.get('departure_description')
            ))

        # === Custom Partner Synchronization After the Write ===
        # Fields to propagate to the related partner (work contact)
        fields_to_sync = ['name', 'phone', 'mobile', 'email', 'job_id', 'image_1920']
        # Mapping from employee fields to partner fields (adjust if your partner fields differ)
        related_fields = {
            'name': 'name',
            'phone': 'phone',
            'mobile': 'mobile',
            'email': 'email',
            'job_id': 'job_description',
            'image_1920': 'image_1920',
        }
        # For each employee record, update its linked work contact (res.partner)
        for employee in self:
            partner = employee.work_contact_id  # assuming work_contact_id is the partner to update
            if partner:
                partner_vals = {}
                for field in fields_to_sync:
                    if field in vals:
                        partner_field = related_fields.get(field, field)
                        partner_vals[partner_field] = vals[field]
                if partner_vals:
                    partner.with_context(skip_employee_update=True).write(partner_vals)

        return res


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