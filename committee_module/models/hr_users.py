from odoo import api, models, fields, _

class User(models.Model):
    _inherit = 'res.users'

    member_type = fields.Selection(related='employee_id.member_type', string='Member Type', readonly=False, store=True)