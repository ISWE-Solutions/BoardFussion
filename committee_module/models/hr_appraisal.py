from odoo import models, fields, api, _

class HrAppraisal(models.Model):
    _inherit = 'hr.appraisal'

    committees_ids = fields.Many2many(related='employee_id.committees_ids')
    manager_ids = fields.Many2many('hr.employee', string='Evaluator')
    employee_feedback_published = fields.Boolean(string="Member Feedback Published", default=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        # Suppress the default "Employee Appraisal created" message
        self = self.with_context(mail_create_nosubscribe=True, mail_create_nolog=True)

        # Call the super method to create the appraisal records
        appraisals = super(HrAppraisal, self).create(vals_list)

        # Manually post a custom message to the chatter
        for appraisal in appraisals:
            appraisal.message_post(body="Member Evaluation created")

        return appraisals