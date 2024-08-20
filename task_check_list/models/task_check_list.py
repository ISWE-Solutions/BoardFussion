from odoo import models, fields, api


class ProjectTask(models.Model):
    _inherit = 'project.task'

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
