from odoo import models, fields, api, _, Command

class HrContract(models.Model):
    _inherit = 'hr.contract'

    resource_calendar_id = fields.Many2one('resource.calendar', readonly=False)