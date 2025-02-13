from odoo import models, fields, api
from odoo.exceptions import RedirectWarning
from odoo.exceptions import ValidationError, UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    employee_ids = fields.One2many('hr.employee', 'partner_id', string="Employees")

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