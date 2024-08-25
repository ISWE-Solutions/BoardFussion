from odoo import models, fields, api, _, Command

class HrContract(models.Model):
    _inherit = 'hr.contract'

    resource_calendar_id = fields.Many2one('resource.calendar', readonly=False)


class HrContractSignDocumentWizard(models.TransientModel):
    _inherit = 'hr.contract.sign.document.wizard'

    employee_ids = fields.Many2many(
        'hr.employee',
        string='Members',  # New label for the field
    )
