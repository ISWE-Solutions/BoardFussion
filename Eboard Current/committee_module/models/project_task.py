from odoo import models, fields, api, Command, _


class ProjectTask(models.Model):
    _inherit = 'project.task'

    calendar_id = fields.Many2one('calendar.event')

    @api.model_create_multi
    def create(self, values):
        rtn = super(ProjectTask, self).create(values)
        print(values)
        # for rec in rtn:
            # rec.product_id = rec.calendar_id.product_id.id
        return rtn