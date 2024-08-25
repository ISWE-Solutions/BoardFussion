from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'
    view_evaluation = fields.Char(string='view evaluation')
    employee_id = fields.Many2one('hr.employee', string='Member')
    partner_id = fields.Many2one('res.partner', string="Member")
    def action_appraisal(self):
        for record in self:

            employee = record.employee_id
            print('employee id ', employee)
            if not employee:
                raise UserError('No employee linked to this survey input.')

            appraisal = self.env['hr.appraisal'].search([('employee_id', '=', employee.id)], limit=1)
            if not appraisal:
                raise UserError('No appraisal found for this employee.')

            return {
                'type': 'ir.actions.act_window',
                'name': 'Appraisal',
                'res_model': 'hr.appraisal',
                'view_mode': 'form',
                'res_id': appraisal.id,
                'target': 'current',
            }



    def action_survey(self):
        print('/survey/start/%s' % self.access_token)
        return '/survey/start/%s' % self.access_token


class SurveyUserInputSub(models.Model):
    _inherit = 'hr.appraisal'
    view_evaluation = fields.Char(string='view evaluation')

    def action_my_button(self):
        # Your button logic here
        # For example, you could return an action or perform some other action
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
