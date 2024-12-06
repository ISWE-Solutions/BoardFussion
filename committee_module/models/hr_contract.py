from odoo import models, fields, api, _, Command

class HrContract(models.Model):
    _inherit = 'hr.contract'

    resource_calendar_id = fields.Many2one('resource.calendar', readonly=False)

    @api.model_create_multi
    def create(self, vals_list):
        # Suppress automatic chatter message "Employee Contract created"
        self = self.with_context(mail_create_nolog=True)

        # Call the super method to create the contracts
        contracts = super(HrContract, self).create(vals_list)

        # Add a custom chatter message "Member Contract created"
        for contract in contracts:
            contract.message_post(body="Member Contract created")

        # Sync contract calendar -> calendar employee (retain your existing logic)
        open_contracts = contracts.filtered(
            lambda c: c.state == 'open' or (
                        c.state == 'draft' and c.kanban_state == 'done' and c.employee_id.contracts_count == 1)
        )
        for contract in open_contracts.filtered(lambda c: c.employee_id and c.resource_calendar_id):
            contract.employee_id.resource_calendar_id = contract.resource_calendar_id

        return contracts


class HrContractSignDocumentWizard(models.TransientModel):
    _inherit = 'hr.contract.sign.document.wizard'

    employee_ids = fields.Many2many(
        'hr.employee',
        string='Members',  # New label for the field
    )
