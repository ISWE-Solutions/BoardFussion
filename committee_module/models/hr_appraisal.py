from odoo import models, fields, api, _

class HrAppraisal(models.Model):
    _inherit = 'hr.appraisal'

    committees_ids = fields.Many2many(related='employee_id.committees_ids')
    manager_ids = fields.Many2many('hr.employee', string='Evaluator')
