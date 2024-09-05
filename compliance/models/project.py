from odoo import models, fields, api


class ProjectProject(models.Model):
    _inherit = 'project.project'

    is_compliance = fields.Boolean(string='Is Compliance', default=False, readonly=True)
    compliance_tag = fields.Many2one('project.tags', string='Compliance Tag')

    def create_compliance_project(self, values):
        values.update({
            'is_compliance': True,
            'compliance_tag': self.env.ref('compliance_project.compliance_tag').id
        })
        return self.create(values)




class ProjectTask(models.Model):
    _inherit = 'project.task'

    task_type = fields.Selection([
        ('action_point', 'Action Point'),
        ('compliance', 'Compliance')
    ], string='Task Type')

    compliance_id = fields.Many2one('project.project', string='Compliance Project')

    @api.model
    def default_get(self, fields_list):
        defaults = super(ProjectTask, self).default_get(fields_list)
        # Check some condition and set the default value
        if self.env.context.get('default_project_id'):
            project = self.env['project.project'].browse(self.env.context.get('default_project_id'))
            if project.is_compliance:
                defaults['task_type'] = 'compliance'
            else:
                defaults['task_type'] = 'action_point'
        else:
            defaults['task_type'] = 'action_point'
        return defaults

