import base64
import logging
from odoo import fields,models, api, _, Command
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError


class AgendaLines(models.Model):
    _name = 'agenda.lines'
    _description = 'Agenda Lines'

    calendar_id = fields.Many2one('calendar.event', string="Calendar")
    description = fields.Html(related='calendar_id.agenda_description')
    partner_ids = fields.Many2many('res.partner', string='Attendees')
    duration = fields.Float(related="calendar_id.duration", string='Duration')
    agenda_attachment_ids = fields.Many2many(comodel_name='ir.attachment', string="Attachments")