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


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    def unlink(self):
        for event in self:
            # Delete the related project with the same name as the calendar event
            related_project = self.env['project.project'].search([('name', '=', event.name)], limit=1)
            if related_project:
                print(f"Found related project: {related_project.name}")
                related_project.unlink()
            else:
                print(f"No related project found for event: {event.name}")

            # Find the "Projects" workspace (folder)
            project_workspace = self.env['documents.folder'].search([('name', '=', 'Projects')], limit=1)
            if project_workspace:
                print(f"Found project workspace: {project_workspace.name}")

                # Search for the related document with the same name as the calendar event in the "Projects" workspace
                related_document = self.env['documents.document'].search([
                    ('name', '=', event.name),
                    ('folder_id', '=', project_workspace.id)
                ], limit=1)

                if related_document:
                    print(f"Found related document: {related_document.name}")
                    related_document.unlink()
                else:
                    print(f"No related document found for event: {event.name} in the Projects workspace")

                # Search for the folder within the "Projects" workspace that matches the event name
                related_folder = self.env['documents.folder'].search([
                    ('name', '=', event.name),
                    # ('parent_id', '=', project_workspace.id)
                ], limit=1)

                if related_folder:
                    print(f"Found related folder: {related_folder.name}")
                    related_folder.unlink()
                else:
                    print(f"No related folder found for event: {event.name} in the Projects workspace")
            else:
                print("No 'Projects' workspace found")

        # Proceed with the deletion of the calendar event
        return super(CalendarEvent, self).unlink()

