from odoo import models, fields, api
from odoo.exceptions import RedirectWarning
from odoo.exceptions import ValidationError, UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    employee_ids = fields.One2many('hr.employee', 'partner_id', string="Employees")

    # def write(self, vals):
    #     # Avoid recursion if the update is already in progress
    #     if self.env.context.get('skip_employee_update', False):
    #         return super(ResPartner, self).write(vals)

    #     # Proceed with the write operation
    #     res = super(ResPartner, self).write(vals)

    #     # Fields to propagate to employees
    #     fields_to_sync = ['name', 'phone', 'mobile', 'email', 'job_description']
    #     related_fields = {
    #         'name': 'name',
    #         'phone': 'work_phone',
    #         'mobile': 'mobile_phone',
    #         'email': 'work_email',
    #         'job_description': 'job_id',
    #     }

    #     # Propagate changes to related employees
    #     for partner in self:
    #         for employee in partner.employee_ids:
    #             employee_vals = {related_fields[field]: vals[field] for field in fields_to_sync if field in vals}
    #             if employee_vals:
    #                 # Set the context flag to avoid recursion during the employee update
    #                 employee.with_context(skip_partner_update=True).write(employee_vals)

    #     return res

    # def toggle_active(self):
    #     super().toggle_active()  # Call the parent method
    
    #     for partner in self:
    #         if not partner.active:
    #             print(f"Archiving partner: {partner.name} (ID: {partner.id})")
    
    #             # Archive associated user, if active
    #             user = self.env['res.users'].search([('partner_id', '=', partner.id), ('active', '=', True)])
    #             if user:
    #                 print(f"Archiving associated user: {user.login}")
    #                 user.write({'active': False})  # Deactivate user
    
    #             # Archive related users through employee_ids if they are active
    #             related_users = self.env['res.users'].search([
    #                 ('employee_ids', 'in', partner.id),
    #                 ('active', '=', True)  # Only consider active users for archiving
    #             ])
    #             if related_users:
    #                 print(f"Found active users related to partner {partner.name}: {[u.login for u in related_users]}")
    #                 related_users.write({'active': False})  # Deactivate related users
    #                 print(f"Archived {len(related_users)} user(s) related to partner {partner.name}")
    #             else:
    #                 print(f"No active users found related to partner {partner.name}")
    
    #         else:
    #             print(f"Activating partner: {partner.name} (ID: {partner.id})")
    
    #             # Unarchive associated user, if archived
    #             user = self.env['res.users'].search([('partner_id', '=', partner.id), ('active', '=', False)])
    #             if user:
    #                 print(f"Unarchiving associated user: {user.login}")
    #                 user.write({'active': True})  # Reactivate user
    
    #             # Unarchive related users through employee_ids if they are archived
    #             related_users = self.env['res.users'].search([
    #                 ('employee_ids', 'in', partner.id),
    #                 ('active', '=', False)  # Only consider archived users for unarchiving
    #             ])
    #             if related_users:
    #                 print(f"Found archived users related to partner {partner.name}: {[u.login for u in related_users]}")
    #                 related_users.write({'active': True})  # Reactivate related users
    #                 print(f"Unarchived {len(related_users)} user(s) related to partner {partner.name}")
    #             else:
    #                 print(f"No archived users found related to partner {partner.name} for unarchiving.")

    def write(self, vals):
        # If this update is triggered by an employee update, do not propagate further.
        if self.env.context.get('skip_employee_update', False):
            return super(ResPartner, self).write(vals)

        # Proceed with the normal partner update.
        res = super(ResPartner, self).write(vals)

        # Define which partner fields should be synced to employees.
        fields_to_sync = ['name', 'phone', 'mobile', 'email', 'image_1920']
        # Mapping: partner field -> employee field.
        mapping = {
            'name': 'name',
            'phone': 'work_phone',
            'mobile': 'mobile_phone',
            'email': 'work_email',
            'image_1920': 'image_1920',
        }

        # For each updated partner record, update linked employees.
        for partner in self:
            employees = self.env['hr.employee'].search([('work_contact_id', '=', partner.id)])
            if employees:
                employee_vals = {}
                for field in fields_to_sync:
                    if field in vals:
                        employee_vals[mapping[field]] = vals[field]
                if employee_vals:
                    # Pass a context flag to prevent the employee write from calling back to partner.
                    employees.with_context(skip_partner_update=True).write(employee_vals)

        return res