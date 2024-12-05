from odoo import api, models, fields, _
from odoo.exceptions import ValidationError

class User(models.Model):
    _inherit = 'res.users'

    member_type = fields.Selection(related='employee_id.member_type', string='Member Type', readonly=False, store=True)

    def write(self, vals):
        res = super(User, self).write(vals)

        # Fields to propagate
        fields_to_sync = ['name', 'phone', 'mobile', 'email', 'job_description']
        for user in self:
            for field in fields_to_sync:
                if field in vals:
                    # Update related employee
                    employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
                    if employee:
                        employee.write({field: vals[field]})

                    # Update related partner
                    if user.partner_id:
                        user.partner_id.write({field: vals[field]})

        return res

    def toggle_active(self):
        super().toggle_active()  # Call the parent method

        for user in self:
            if not user.active:  # User is being archived
                print(f"Archiving user: {user.login} (ID: {user.id})")

                # Check if there is an associated employee record
                employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)

                if not employee:  # Only proceed if no associated employee
                    # Archive related partners
                    partners_to_archive = self.env['res.partner'].search([
                        '|',  # Use OR to search for both conditions
                        ('employee_ids.user_id', '=', user.id),  # Partners related via employee_ids
                        ('id', '=', user.partner_id.id),  # Partners linked via partner_id
                        ('active', '=', True)  # Only consider active partners for archiving
                    ])

                    if partners_to_archive:
                        print(
                            f"Found active partners related to user {user.login}: {[partner.name for partner in partners_to_archive]}")
                        partners_to_archive.write({'active': False})  # Deactivate partners
                        print(f"Archived {len(partners_to_archive)} partner(s) related to user {user.login}")
                    else:
                        print(f"No active partners found related to user {user.login}.")
                else:
                    print(f"User {user.login} has an associated employee. Skipping partner archiving.")

    def unlink(self):
        for user in self:
            # Check if there is an associated employee record
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)

            if employee:  # User has an associated employee
                print(f"User {user.login} has an associated employee. Archiving user only.")
                user.active = False  # Archive the user

            else:  # No associated employee
                print(f"User {user.login} has no associated employee. Deleting user and archiving partners.")

                # Archive the user first
                user.active = False  # Archive the user

                # Archive related partners
                partners_to_archive = self.env['res.partner'].search([
                    '|',  # Use OR to search for both conditions
                    ('employee_ids.user_id', '=', user.id),  # Partners related via employee_ids
                    ('id', '=', user.partner_id.id),  # Partners linked via partner_id
                    ('active', '=', True)  # Only consider active partners for archiving
                ])

                if partners_to_archive:
                    partners_to_archive.write({'active': False})  # Deactivate partners
                    print(f"Archived {len(partners_to_archive)} partner(s) related to user {user.login}")
                else:
                    print(f"No active partners found related to user {user.login}.")

        # Note: Do not call super().unlink() since we are archiving instead of deleting