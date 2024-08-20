from odoo import models, fields, api
from datetime import timedelta


CLOSED_STATES = {
    '1_done': 'Done',
    '1_canceled': 'Canceled',
}


class Task(models.Model):
    _inherit = "project.task"

    # parent_id = fields.Many2one('calendar.event', string='Parent Task', index=True, tracking=True)
    # child_ids = fields.One2many('project.task', 'project_task_id', string="Sub-tasks")
    project_child_ids = fields.One2many('calendar.line', 'project_task_id', string="Sub-tasks")

    task_id = fields.Many2one('project.task', string='Related Task')
    # personal_stage_type_id = fields.Many2one('your.model.name', string='Personal Stage Type')
    milestone_id = fields.Many2one('project.milestone', string='Milestone')

    video_attachment_ids = fields.One2many(comodel_name='video.attachment', inverse_name='calendar_id', string="Attachments")
    mom_description = fields.Html(name="mom_description", string="Description")

    # @api.model
    # def create(self, vals):
    #     task = super(Task, self).create(vals)
    #     return task

    # def action_create_meeting(self):
    #     vals = []
    #     for task in self.project_child_ids:
    #         vals.append({
    #             'name': f"Meeting for {task.task_name}",
    #             'start': task.start_date,
    #             'stop': task.end_date,
    #             'user_id':task.organizer.id,
    #             'partner_ids':task.partner_ids
    #         })
    #     meeting = self.env['calendar.event'].create(vals)

class CalanderMeeting(models.Model):
    _name = 'calendar.line'

    task_name = fields.Char(string="Task")
    start_date = fields.Datetime(string="From")
    end_date = fields.Datetime(string="To")
    organizer = fields.Many2one(comodel_name="res.users", string="Responsible")
    partner_ids= fields.Many2many(comodel_name="res.partner", string="Participants")
    project_task_id = fields.Many2one('project.task')
    calendar_id = fields.Many2one('calendar.event')

    def action_create_meeting(self):
        vals = []
        for task in self:
            vals.append({
                'name': f"Meeting for {task.task_name}",
                'start': task.start_date,
                'stop': task.end_date,
                'user_id':task.organizer.id,
                'partner_ids':task.partner_ids
            })
        meeting = self.env['calendar.event'].create(vals)
        if meeting:
            self.calendar_id = meeting.id