from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProjectProject(models.Model):
    _inherit = 'project.project'

    is_compliance = fields.Boolean(string='Is Compliance', default=False, readonly=True)
    compliance_tag = fields.Many2one('project.tags', string='Compliance Tag')
    project_progress = fields.Float(compute='_compute_project_progress', string='', store=True)
    max_progress = fields.Float(string='Max Progress', default=100)

    def create_compliance_project(self, values):
        values.update({
            'is_compliance': True,
            'compliance_tag': self.env.ref('compliance_project.compliance_tag').id
        })
        return self.create(values)

    @api.depends('task_ids.checklist_progress')  # Dependent on the progress of all tasks in the project
    def _compute_project_progress(self):
        for project in self:
            total_tasks = len(project.task_ids)
            if total_tasks:
                progress_sum = sum(task.checklist_progress for task in project.task_ids)
                project.project_progress = round(progress_sum / total_tasks, 2)
            else:
                project.project_progress = 0


class ProjectTask(models.Model):
    _inherit = 'project.task'

    task_type = fields.Selection([
        ('action_point', 'Action Point'),
        ('compliance', 'Compliance')
    ], string='Task Type')

    compliance_id = fields.Many2one('project.project', string='Compliance Project')

    task_checklist_ids = fields.One2many('task.checklist', 'task_id', string='Task Checklists')
    checklist_progress = fields.Float(compute='_compute_checklist_progress', string='Overall Progress', store=True)
    max_rate = fields.Integer(string='Maximum Rate', default=100)

    @api.depends('task_checklist_ids.progress')
    def _compute_checklist_progress(self):
        for task in self:
            total_checklists = len(task.task_checklist_ids)
            if total_checklists:
                progress_sum = sum(task.task_checklist_ids.mapped('progress'))
                task.checklist_progress = round(progress_sum / total_checklists, 2)
            else:
                task.checklist_progress = 0

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


class TaskChecklist(models.Model):
    _name = 'task.checklist'
    _description = 'Checklist for the task'

    name = fields.Char(string='Checklist Items', required=True)
    task_id = fields.Many2one('project.task', string='Task', ondelete='cascade')
    progress = fields.Float(string='Progress', default=0.0)
    is_done = fields.Boolean(string='Done', compute='_compute_is_done', store=True)

    @api.depends('progress')
    def _compute_is_done(self):
        for checklist in self:
            checklist.is_done = checklist.progress == 100

    @api.constrains('progress')
    def _check_progress(self):
        for record in self:
            if record.progress > 100:
                raise ValidationError('Progress must not be more than 100.')
