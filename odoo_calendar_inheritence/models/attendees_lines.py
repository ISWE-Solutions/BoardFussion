from odoo import models, fields, api, _, Command

class AttendeesLines(models.Model):
    _name ='attendees.lines'

    attendee_name = fields.Char(string='Attendee')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    has_attended = fields.Boolean(default=True)
    calendar_id = fields.Many2one('calendar.event', string='Calendar')