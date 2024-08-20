from odoo import api, models, fields, _


class User(models.Model):
    _inherit = ['res.users']

    member_type = fields.Selection([
        ('board_member', 'Board Member'),
        ('employee', 'Employee'),
    ], string='Member Type', default='board_member', required=True)