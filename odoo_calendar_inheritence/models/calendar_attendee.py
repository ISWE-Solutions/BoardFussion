import base64
import logging
from odoo import fields,models, api, _, Command
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context

class Calendar_attendee(models.Model):
    _inherit = 'calendar.attendee'


    role_id = fields.Many2one(
        'calendar.attendee.role',
        string="Role",
        ondelete='restrict',
        help="Select or create an attendee role."
    )

    def _send_mail_to_attendees(self, template):
        # Overriding the email sending method to disable sending emails.
        # Returning True to mimic a successful email send without doing anything.
        return True

    def _send_custom_mail_to_attendees(self, mail_template, force_send=True):
        """ Send mail for event invitation to event attendees.
            :param mail_template: a mail.template record
            :param force_send: if set to True, the mail(s) will be sent immediately (instead of the next queue processing)
        """
        if isinstance(mail_template, str):
            raise ValueError('Template should be a template record, not an XML ID anymore.')
        if self.env['ir.config_parameter'].sudo().get_param('calendar.block_mail') or self._context.get(
                "no_mail_to_attendees"):
            return False
        if not mail_template:
            _logger.warning("No template passed to %s notification process. Skipped.", self)
            return False

        # get ics file for all meetings
        ics_files = self.mapped('event_id')._get_ics_file()

        for attendee in self:
            if attendee.email and attendee._should_notify_attendee():
                event_id = attendee.event_id.id
                ics_file = ics_files.get(event_id)

                attachment_ids = mail_template.attachment_ids.ids
                if ics_file:
                    context = {
                        **clean_context(self.env.context),
                        'no_document': True,  # An ICS file must not create a document
                    }
                    attachment_ids += self.env['ir.attachment'].with_context(context).create({
                        'datas': base64.b64encode(ics_file),
                        'description': 'invitation.ics',
                        'mimetype': 'text/calendar',
                        'res_id': event_id,
                        'res_model': 'calendar.event',
                        'name': 'invitation.ics',
                    }).ids

                body = mail_template._render_field(
                    'body_html',
                    attendee.ids,
                    compute_lang=True)[attendee.id]
                subject = mail_template._render_field(
                    'subject',
                    attendee.ids,
                    compute_lang=True)[attendee.id]
                attendee.event_id.with_context(no_document=True).sudo().message_notify(
                    email_from=attendee.event_id.user_id.email_formatted or self.env.user.email_formatted,
                    author_id=attendee.event_id.user_id.partner_id.id or self.env.user.partner_id.id,
                    body=body,
                    subject=subject,
                    partner_ids=attendee.partner_id.ids,
                    email_layout_xmlid='mail.mail_notification_light',
                    attachment_ids=attachment_ids,
                    force_send=force_send,
                )


class CalendarAttendeeRole(models.Model):
    _name = 'calendar.attendee.role'
    _description = 'Attendee Role'

    name = fields.Char(string="Role Name", required=True)
