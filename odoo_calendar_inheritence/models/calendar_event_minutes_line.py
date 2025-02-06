
from markupsafe import Markup
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError, AccessError
import base64
import logging
from bs4 import BeautifulSoup
from odoo.tools import html2plaintext

_logger = logging.getLogger()


class CalendarEventMinutesLine(models.Model):
    _name = 'calendar.event.minutes.line'
    _description = 'Calendar Event minutes Line'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', default=10)
    product_id = fields.Many2one('product.template', string="Product")
    product_document_id = fields.Many2one('product.document', string="Product Document")
    quantity = fields.Float(string="Quantity")
    uom_id = fields.Many2one('uom.uom', string="Unit of Measure")
    agenda = fields.Char(string='Agenda', default=_('new'))
    presenter_id = fields.Many2many(
        'res.partner',
        'calendar_event_minutes_line_presenter_id_rel',
        store=True,
    )

    duration = fields.Float(string="Duration")
    start_date = fields.Datetime(string='Start Date', default=lambda self: fields.Datetime.now())
    end_date = fields.Datetime(string='End Date')
    description = fields.Html(string='Description')
    time = fields.Char(string='Time')
    pdf_attachment = fields.Many2many('ir.attachment', string='Add Attachments')
    calendar_id = fields.Many2one('calendar.event', string="Calendar Event", required=True)
    Restricted = fields.Many2many(
        'res.partner',
        'calendar_event_minutes_line_Restricted_rel',
        string="Visible to:",
        store=True,
    )

    is_user_restricted = fields.Boolean(compute='_compute_is_user_restricted', store=False)
    confidential = fields.Boolean(string="Confidential", default=False)

    document_names = fields.Char(string="Document Names", compute="_compute_document_names", store=False)

    user_is_board_member_or_secretary = fields.Boolean(compute='_compute_user_is_board_member_or_secretary',
                                                       store=False)

    @api.depends('Restricted')
    def _compute_is_user_restricted(self):
        for record in self:
            record.is_user_restricted = self.env.user.partner_id not in record.Restricted

    @api.depends('pdf_attachment')
    def _compute_document_names(self):
        for line in self:
            document_names = line.pdf_attachment.mapped('name')
            line.document_names = ', '.join(document_names)


    @api.onchange('minutes_line_ids')
    def _onchange_minutes_line_ids(self):
        for record in self:
            if record.confidential and not record.user_is_board_member_or_secretary:
                raise AccessError("You do not have the required permissions to edit this item.")

    @api.model
    def check_access(self):
        if self.confidential and not self.env.user.has_group(
                'odoo_calendar_inheritence.group_agenda_meeting_board_secretary'):
            raise AccessError('You do not have access to this form.')

    @api.onchange('Restricted')
    def _onchange_restricted(self):
        """
        Ensure changes to `Restricted` are reflected in `partner_ids` of the related `product.document`.
        """
        for record in self:
            if record.product_document_id:
                record.product_document_id.partner_ids = record.Restricted

    @api.onchange('confidential')
    def _onchange_confidential(self):
        for record in self:
            if record.confidential and record.calendar_id:
                # Get board member and board secretary groups
                board_member_group = self.env.ref('odoo_calendar_inheritence.group_agenda_meeting_board_member',
                                                  raise_if_not_found=False)
                board_secretary_group = self.env.ref('odoo_calendar_inheritence.group_agenda_meeting_board_secretary',
                                                     raise_if_not_found=False)

                if board_member_group or board_secretary_group:
                    # Fetch all attendees in the Restricted field who are part of either group
                    board_member_partners = self.env['res.partner'].search([
                        ('user_ids.groups_id', 'in', board_member_group.id if board_member_group else 0)
                    ])
                    board_secretary_partners = self.env['res.partner'].search([
                        ('user_ids.groups_id', 'in', board_secretary_group.id if board_secretary_group else 0)
                    ])
                    valid_partners = (board_member_partners | board_secretary_partners).ids

                    # Filter Restricted to keep only valid partners
                    record.Restricted = [(6, 0, list(set(valid_partners) & set(record.Restricted.ids)))]
                else:
                    # If groups are not defined, clear the Restricted list
                    record.Restricted = [(5,)]
            elif not record.confidential:
                # When confidential is set to False, keep the original attendees
                record.Restricted = record.calendar_id.partner_ids.ids

    @api.depends('confidential')
    def _compute_user_is_board_member_or_secretary(self):
        user = self.env.user
        group_ids = user.groups_id.ids
        board_member_group = self.env.ref('odoo_calendar_inheritence.group_agenda_meeting_board_member').id
        secretary_group = self.env.ref('odoo_calendar_inheritence.group_agenda_meeting_board_secretary').id
        self.user_is_board_member_or_secretary = (board_member_group in group_ids or secretary_group in group_ids)

    @api.model_create_multi
    def create(self, values):
        records = super().create(values)
        records._process_minutes_line()
        records._update_calendar_status()
        return records

    def write(self, values):
        res = super().write(values)
        self._process_minutes_line()
        return res

    def _process_minutes_line(self):
        """Handles logic for processing product documents and attachments."""
        document_model = self.env['product.document']
        success = True
        message = _("Minutes processed successfully.")
        message_type = "success"

        try:
            for record in self:
                if not record.product_id:
                    record.product_id = record.calendar_id.product_id.id

                product = record.product_id

                # Ensure product_document_id is set
                if not record.product_document_id:
                    new_document = document_model.sudo().create({
                        'res_model': 'product.template',
                        'name': product.display_name,
                        'res_id': product.id,
                    })
                    record.product_document_id = new_document.id
                    _logger.info(
                        f"Assigned product_document_id {new_document.id} to Calendar Event Minutes Line {record.id}"
                    )

                if record.pdf_attachment:
                    existing_docs = document_model.sudo().search([
                        ('ir_attachment_id', 'in', record.pdf_attachment.ids),
                        ('res_model', '=', 'product.template'),
                        ('res_id', '=', product.id),
                    ])
                    existing_attachment_ids = existing_docs.mapped('ir_attachment_id.id')

                    for attachment in record.pdf_attachment:
                        if attachment.id not in existing_attachment_ids:  # Prevent duplicate processing
                            attachment.write({
                                'res_model': 'calendar.event',
                                'res_id': record.calendar_id.id,
                            })

                            restricted_partner_ids = list(set(record.Restricted.ids))
                            new_document = document_model.sudo().create({
                                'res_model': 'product.template',
                                'name': attachment.name,
                                'res_id': product.id,
                                'ir_attachment_id': attachment.id,
                                'partner_ids': [(6, 0, restricted_partner_ids)]
                            })
                            _logger.info(
                                f"Created new Minute document {new_document.id} for attachment {attachment.id} "
                                f"and linked it to Calendar Event {record.calendar_id.id}"
                            )

                # Set is_minutes_created to True on the associated calendar.event
                if record.calendar_id and not record.calendar_id.is_minutes_created:
                    record.calendar_id.is_minutes_uploaded = True
                    record.calendar_id.is_minutes_published = True
                    _logger.info(f"Set is_minutes_created to True for Calendar Event {record.calendar_id.id}")

        except Exception as e:
            success = False
            message = _("An error occurred while processing minutes: %s") % str(e)
            message_type = "danger"
            _logger.error(message)

        # Return a notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Notification"),
                'message': message,
                'type': message_type,  # 'success', 'warning', 'danger', or 'info'
                'sticky': False,  # Notification disappears after some time
            },
        }

    def _update_calendar_status(self):
        """Updates the status fields on the related calendar event when minutes are successfully saved."""
        for record in self:
            if record.id:  # Ensure the record is not a draft (checking if it has been saved)
                upload_type = self.env.context.get('upload_type')
                confidential = self.env.context.get('default_confidential', False)

                if upload_type == "confidential":
                    record.calendar_id.is_confidential_minutes_uploaded = True
                elif upload_type == "non_confidential":
                    record.calendar_id.is_non_confidential_minutes_uploaded = True

    @api.model
    def delete_all_for_calendar_event(self, calendar_event_id):
        """Delete all minutes line records linked to the specified calendar event.

        Args:
            calendar_event_id (int): ID of the calendar.event to delete linked records for.
        """
        records = self.search([('calendar_id', '=', calendar_event_id)])
        records.unlink()
        return True

