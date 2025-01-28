from email.policy import default

from markupsafe import Markup
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError, AccessError
import base64
import logging
from bs4 import BeautifulSoup
from odoo.tools import html2plaintext

_logger = logging.getLogger()


class CalendarEventProductLine(models.Model):
    _name = 'calendar.event.product.line'
    _description = 'Calendar Event Product Line'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', default=10)
    product_id = fields.Many2one('product.template', string="Product")
    product_document_id = fields.Many2one('product.document', string="Product Document")
    quantity = fields.Float(string="Quantity")
    uom_id = fields.Many2one('uom.uom', string="Unit of Measure")
    agenda = fields.Char(string='Agenda', default=_('new'))
    presenter_id = fields.Many2many(
        'res.partner',
        'calendar_event_product_line_presenter_id_rel',
        store=True,
    )

    is_minutes_created = fields.Boolean(default="false")

    duration = fields.Float(string="Duration")
    start_date = fields.Datetime(string='Start Date', default=lambda self: fields.Datetime.now())
    end_date = fields.Datetime(string='End Date')
    description = fields.Html(string='Description')
    time = fields.Char(string='Time')
    pdf_attachment = fields.Many2many('ir.attachment', string='Add Attachments')
    calendar_id = fields.Many2one('calendar.event', string="Calendar Event", required=True)

    Restricted = fields.Many2many(
        'res.partner',
        'calendar_event_product_line_Restricted_rel',
        string="Visible to:",
        store=True,
    )

    is_user_restricted = fields.Boolean(compute='_compute_is_user_restricted', store=False)
    confidential = fields.Boolean(string="Confidential", default=False)

    document_names = fields.Char(string="Document Names", compute="_compute_document_names", store=False)

    user_is_board_member_or_secretary = fields.Boolean(compute='_compute_user_is_board_member_or_secretary',
                                                       store=False)
    display_description = fields.Char(string='Display Agenda Item', compute='_compute_display_description')
    presenter_domain_ids = fields.Json(
        string="Presenter Domain",
        compute="_compute_presenter_domain_ids",
        store=False,
    )


    @api.onchange('description')
    def _onchange_description_attachment(self):
        """
        Trigger an update on the parent calendar.event when a new attachment is added or modified.
        """
        for record in self:
            if record.calendar_id:
                record.calendar_id.write({
                    'last_write_date': fields.Datetime.now()  # You can update any field here as needed
                })


    @api.depends('calendar_id')
    def _compute_presenter_domain_ids(self):
        for record in self:
            if record.calendar_id and record.calendar_id.partner_ids:
                record.presenter_domain_ids = record.calendar_id.partner_ids.ids
                # _logger.info(f"Computed presenter_domain_ids: {record.presenter_domain_ids}")
            else:
                record.presenter_domain_ids = []
                # _logger.info("No calendar_id or no partner_ids found; presenter_domain_ids is empty.")

    @api.onchange('product_line_ids')
    def _onchange_product_line_ids(self):
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

    @api.depends('confidential', 'user_is_board_member_or_secretary', 'description')
    def _compute_display_description(self):
        for record in self:
            if record.confidential and not record.user_is_board_member_or_secretary:
                record.display_description = 'Confidential'
            else:
                record.display_description = html2plaintext(record.description or "")

    @api.depends('Restricted')
    def _compute_is_user_restricted(self):
        for record in self:
            record.is_user_restricted = self.env.user.partner_id not in record.Restricted

    @api.depends('pdf_attachment')
    def _compute_document_names(self):
        for line in self:
            document_names = line.pdf_attachment.mapped('name')
            line.document_names = ', '.join(document_names)

    @api.model_create_multi
    def create(self, values):
        rtn = super(CalendarEventProductLine, self).create(values)
        document_model = self.env['product.document']

        for record in rtn:
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
                    f"Assigned product_document_id {new_document.id} to Calendar Event Product Line {record.id}")

            # Process PDF attachments
            if record.pdf_attachment:
                for attachment in record.pdf_attachment:
                    _logger.info(f"Processing attachment: {attachment.name}")
                    restricted_partner_ids = list(set(record.Restricted.ids))
                    # Create new document for each attachment
                    new_document = document_model.sudo().create({
                        'res_model': 'product.template',
                        'name': attachment.name,
                        'res_id': product.id,
                        'ir_attachment_id': attachment.id,
                        'partner_ids': [(6, 0, restricted_partner_ids)]
                    })
                    _logger.info(f"Created new product document {new_document.id} for attachment {attachment.id}")

                    # Call the `delete_article` method from the related calendar
            if record.calendar_id and hasattr(record.calendar_id, 'delete_article'):
                _logger.info(f"Calling delete_article for Calendar Event {record.calendar_id.id}")
                record.calendar_id.delete_article()

        return rtn

    @api.model
    def write(self, values):
        res = super(CalendarEventProductLine, self).write(values)
        document_model = self.env['product.document']

        for record in self:
            # Update product_id if calendar_id changes
            if 'calendar_id' in values:
                record.product_id = record.calendar_id.product_id.id

            product = record.product_id

            # Ensure product_document_id is set
            if 'product_document_id' not in values and not record.product_document_id:
                new_document = document_model.sudo().create({
                    'res_model': 'product.template',
                    'name': product.display_name,
                    'res_id': product.id,
                })
                record.product_document_id = new_document.id
                _logger.info(
                    f"Assigned product_document_id {new_document.id} to Calendar Event Product Line {record.id}")

            # Process PDF attachments
            if 'pdf_attachment' in values:
                existing_documents = document_model.sudo().search( [('ir_attachment_id', 'in', record.pdf_attachment.ids)])
                attachment_ids = record.pdf_attachment.ids
                for attachment in record.pdf_attachment:
                    if not existing_documents.filtered(lambda doc: doc.ir_attachment_id.id == attachment.id):
                        _logger.info(f"Processing new attachment: {attachment.name}")
                        restricted_partner_ids = list(set(record.Restricted.ids))
                        # Create new document for each attachment
                        new_document = document_model.sudo().create({
                            'res_model': 'product.template',
                            'name': attachment.name,
                            'res_id': product.id,
                            'ir_attachment_id': attachment.id,
                            'partner_ids': [(6, 0, restricted_partner_ids)]
                        })
                        _logger.info(f"Created new product document {new_document.id} for attachment {attachment.id}")

            # Handle Restricted and partner_ids synchronization on update
            if 'Restricted' in values:
                restricted_partner_ids = list(set(record.Restricted.ids))
                # Update partner_ids for related documents
                for document in document_model.sudo().search([('ir_attachment_id', 'in', record.pdf_attachment.ids)]):
                    document.partner_ids = [(6, 0, restricted_partner_ids)]
                _logger.info(f"Updated partner_ids for product documents linked to product {product.id}")

            # Recalculate visible users after updates
            record.calendar_id.compute_visible_users(product_document_ids=record.product_document_id)

        return res

    def unlink(self):
        unlink_list_ids = []
        for record in self:
            if record.pdf_attachment:
                unlink_res = self.env['product.document'].sudo().search(
                    [('ir_attachment_id', 'in', record.pdf_attachment.ids)])
                if unlink_res:
                    unlink_res.sudo().unlink()
        res = super(CalendarEventProductLine, self).unlink()
        return res

    def _create_subtask(self):
        project_task_model = self.env['project.task']
        for line in self:
            project_name = line.calendar_id.name
            project_id = line.calendar_id.project_id.id
            parent_task_id = line.calendar_id.task_id.id if line.calendar_id.task_id else False
            if not project_id:
                raise ValidationError(_('The project is not set for the calendar event.'))
            task_vals = {
                'name': project_name,
                'project_id': project_id,
                # 'parent_id': parent_task_id,
                'description': line.description or '',
                'user_ids': [(6, 0, line.presenter_id.ids)],
                'date_deadline': line.end_date,
            }
            project_task_model.create(task_vals)

    def action_create_html(self):
        active_id = self.product_id.product_document_ids.id
        company_id = self.env.company.id
        html = Markup(
            '<a href="/web?#active_id=%d&amp;action=qxm_product_pdf_annotation_tool.product_pdf_annotation&amp;cids=%d" style="padding: 5px 10px; color: #FFFFFF; text-decoration: none; background-color: #875A7B; border: 1px solid #875A7B; border-radius: 3px">View</a>') % (
                   active_id, company_id)
        vals = {'name': "PDF test", 'body': html}
        res = self.env['knowledge.article'].sudo().create(vals)
        # _logger.info(res)

    def _check_unique_agenda(self, agenda, exclude_id=None):
        domain = [('agenda', '=', agenda)]
        if exclude_id:
            domain.append(('id', '!=', exclude_id))
        if self.search_count(domain):
            raise ValidationError(_('The agenda "%s" already exists! Please change the name.') % agenda)

    @api.model
    def _delete_unused_dummy_products(self):
        dummy_category = self.env.ref('odoo_calendar_inheritence.product_category_dummy')
        product_lines = self.search([]).mapped('product_id.id')
        products_to_delete = self.env['product.template'].search([
            ('categ_id', '=', dummy_category.id),
            ('id', 'not in', product_lines)
        ])
        products_to_delete.unlink()

    def action_open_documents(self):
        self.ensure_one()
        company_id = self.env.company.id

        # Collect the attachment IDs from the `pdf_attachment` field.
        attachment_ids = self.pdf_attachment.ids

        # Debug logs
        _logger.info(f"Company ID: {company_id}")
        _logger.info(f"Current Product Line ID: {self.id}")
        _logger.info(f"Attachment IDs in pdf_attachment: {attachment_ids}")

        # Check if there are any matching product documents
        matching_documents = self.env['product.document'].search([('ir_attachment_id', 'in', attachment_ids)])
        _logger.info(f"Matching Product Document IDs: {matching_documents.ids}")

        # Allow action only if the user is NOT restricted
        if self.is_user_restricted:
            raise AccessError(_("You are not allowed to view these documents."))

        return {
            'name': _('Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.document',
            'view_mode': 'kanban,tree,form',
            'context': {
                'default_res_model': 'product.template',
                'default_res_id': self.product_id.id,
                'default_company_id': company_id,
            },
            'domain': [
                ('ir_attachment_id', 'in', attachment_ids),
            ],
            'target': 'current',
            'help': """
                <p class="o_view_nocontent_smiling_face">
                    %s
                </p>
                <p>
                    %s
                    <br/>
                </p>
            """ % (
                _("Upload Documents to your agenda"),
                _("Use this feature to store Documents you would like to share with your members"),
            )
        }


