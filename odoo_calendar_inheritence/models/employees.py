from odoo import models, fields, api



# class SurveyEmployees(models.Model):
#     _inherit = "survey.survey"
#
#     survey_type = fields.Selection(selection_add=[
#         ('compliance', 'Compliance'),
#     ], string="Survey Type", ondelete={'compliance': 'cascade'})


class Department(models.Model):
    _inherit = "hr.department"

    def _compute_total_employee(self):
        result = {}
        count_total_employee = 0
        emp_data = self.env['hr.employee'].search([])

        for department in self.ids:
            for employee in emp_data:
                for committee in employee.committees_ids:
                    if committee.id == department:
                        count_total_employee += 1
            result[department] = count_total_employee
            count_total_employee = 0
        for department in self:
            department.total_employee = result.get(department.id, 0)

