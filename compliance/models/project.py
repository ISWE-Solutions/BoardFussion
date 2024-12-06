from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProjectProject(models.Model):
    _inherit = 'project.project'

    is_compliance = fields.Boolean(string='Is Compliance', default=False, readonly=True)
    compliance_tag = fields.Many2one('project.tags', string='Compliance Tag')
    project_progress = fields.Float(compute='_compute_project_progress', string='', store=True)
    max_progress = fields.Float(string='Max Progress', default=100)

    @api.model_create_multi
    def create(self, vals_list):
        # Prevent double project creation and suppress automatic chatter messages
        self = self.with_context(mail_create_nosubscribe=True, mail_create_nolog=True)

        # Apply the existing logic for project creation
        if any('label_tasks' in vals and not vals['label_tasks'] for vals in vals_list):
            task_label = _("Tasks")
            for vals in vals_list:
                if 'label_tasks' in vals and not vals['label_tasks']:
                    vals['label_tasks'] = task_label

        if len(self.env.companies) > 1 and self.env.user.has_group('project.group_project_stages'):
            # Handle stage assignment based on the context or default
            stage = self.env['project.project.stage'].browse(
                self._context['default_stage_id']) if 'default_stage_id' in self._context else self._default_stage_id()
            if stage.company_id:
                for vals in vals_list:
                    vals['company_id'] = stage.company_id.id

        # Call the super method to create the projects
        projects = super(ProjectProject, self).create(vals_list)

        # Add custom chatter messages
        for project in projects:
            if project.is_compliance:
                project.message_post(body="Compliance created")
            else:
                project.message_post(body="Action Point created")

        return projects

    def create_compliance_project(self, values):
        # Update values for compliance projects
        values.update({
            'is_compliance': True,
            'compliance_tag': self.env.ref('compliance_project.compliance_tag').id
        })
        # Directly call the create method
        return self.create([values])

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
            
    @api.onchange('progress')
    def _progress_check(self):
        if self.progress > 100:
            raise ValidationError('Progress must not be more than 100.')

    @api.constrains('progress')
    def _check_progress(self):
        for record in self:
            if record.progress > 100:
                raise ValidationError('Progress must not be more than 100.')
