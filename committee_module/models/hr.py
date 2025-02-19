from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging



class HrTimesheet(models.Model):
    _inherit = 'account.analytic.line'

    employee_id = fields.Many2one(string='Member')
    project_id = fields.Many2one(string='Action Point')


class Onboarding(models.Model):
    _inherit = 'mail.activity.plan.template'

    employee_role_id = fields.Many2one(string='Member Role')