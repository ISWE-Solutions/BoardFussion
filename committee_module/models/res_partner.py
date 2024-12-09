from odoo import models, fields, api
from odoo.exceptions import RedirectWarning
from odoo.exceptions import ValidationError, UserError

class ContactUpdateWizard(models.TransientModel):
    _name = 'contact.update.wizard'
    _description = 'Contact Update Wizard'

    prompt_text = fields.Text(string="Prompt Text", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Related Partner", readonly=True)

    def confirm_update(self):
        # Trigger the employee update when the user confirms the update
        self.partner_id._update_employee()

        # Close the wizard after confirmation
        return {'type': 'ir.actions.act_window_close'}

class ResPartner(models.Model):
    _inherit = 'res.partner'

    employee_ids = fields.One2many('hr.employee', 'partner_id', string="Employees")

    def write(self, vals):
        # Proceed with the write operation
        res = super(ResPartner, self).write(vals)

        # Trigger the popup only after the save
        self._trigger_update_popup()
        return res

    def _trigger_update_popup(self):
        # Trigger the wizard (popup) after contact update
        return {
            'name': 'contact.update.wizard',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'contact.update.wizard',
            'target': 'new',  # Open in a new window (popup)
            'context': {
                'default_prompt_text': f"The contact '{self.name}' has been updated successfully.",
                'default_partner_id': self.id,  # Pass the current partner_id to the wizard
            },
        }

    def action_update_employees(self):
        self._update_employee()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Employee Updates",
                'message': f"Members linked to {len(self)} partner(s) were successfully updated.",
                'type': 'success',  # types: success, warning, danger, info
                'sticky': False,
            },
        }

    def _update_employee(self):
        # Fields to propagate to employees
        fields_to_sync = ['name', 'phone', 'mobile', 'email', 'job_description']
        related_fields = {
            'name': 'name',
            'phone': 'work_phone',
            'mobile': 'mobile_phone',
            'email': 'work_email',
            'job_description': 'job_id',
        }

        # Propagate changes to related employees
        for partner in self:
            for employee in partner.employee_ids:
                # Build a dictionary of fields to update
                employee_vals = {
                    related_fields[field]: getattr(partner, field, None)
                    for field in fields_to_sync
                    if getattr(partner, field, None)  # Ensure the field exists and has a value
                }

                if employee_vals:
                    # Prevent recursion during the employee update
                    employee.with_context(skip_partner_update=True).write(employee_vals)

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