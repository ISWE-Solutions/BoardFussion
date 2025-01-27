from PyPDF2 import PdfFileMerger
from odoo.exceptions import UserError
import base64
import io
import logging
from markupsafe import Markup
from odoo.tools.safe_eval import safe_eval
from odoo.tools import html_escape
from odoo import models, fields, api, _


_logger = logging.getLogger(__name__)

class ProductDocument(models.Model):
    _inherit = 'product.document'

    pdf_attachment_ids = fields.Many2many('ir.attachment', string='PDF Files')
    merged_pdf = fields.Binary(string='Merged PDF', readonly=True)
    product_document_id = fields.Many2one('product.document', string='Document ID')
    shown_on_product_page = fields.Boolean(default=True, store=True)
    user_ids = fields.Many2many('res.users')
    ir_attachment_custom_id = fields.Many2one('ir.attachment')
    mime_type = fields.Char(related='ir_attachment_id.mimetype')
    is_pdf = fields.Boolean(string='Is PDF Document', compute='_compute_is_pdf_document')
    partner_ids = fields.Many2many('res.partner', string="Document visible to:")

    # is_board_secretary = fields.Boolean(compute='_compute_is_board_secretary')
    is_board_secretary = fields.Boolean(store="True", default="True")

    @api.depends_context('uid')
    def _compute_is_board_secretary(self):
        _logger.info('Computing is_board_secretary for user %s', self.env.user.name)
        user = self.env.user
        group_ids = user.groups_id.ids
        secretary_group = self.env.ref('odoo_calendar_inheritence.group_agenda_meeting_board_secretary').id
        self.user_is_board_member_or_secretary = (secretary_group in group_ids)

    def _onchange_partner_ids(self):
        """
        Ensure changes to `partner_ids` are reflected in `Restricted` of related `calendar.event.product.line` records.
        Avoid recursion by checking if an update is actually required.
        """
        _logger.info("Onchange triggered for partner_ids: %s", self.partner_ids)
        if not self.partner_ids:
            _logger.info("No partners selected, exiting onchange.")
            return

        # Find related calendar event product lines
        product_lines = self.env["calendar.event.product.line"].search([
            ("pdf_attachment", "in", self.ir_attachment_id.ids)
        ])
        _logger.info("Found product lines: %s", product_lines)

        for line in product_lines:
            if line.Restricted != self.partner_ids:
                _logger.info("Updating Restricted for product line ID %s with partners: %s", line.id, self.partner_ids)
                line.write({"Restricted": [(6, 0, self.partner_ids.ids)]})

    def write(self, vals):
        """
        Override the write method to invoke `_onchange_partner_ids` when `partner_ids` is updated.
        """
        res = super(ProductDocument, self).write(vals)

        if "partner_ids" in vals:
            _logger.info("Partner_ids updated in write method for records: %s", self.ids)
            # Call the onchange logic explicitly without recursion
            self._onchange_partner_ids()

        return res



    @api.depends('ir_attachment_id')
    def _compute_is_pdf_document(self):
        for rec in self:
            if rec.ir_attachment_id:
                if rec.ir_attachment_id.mimetype == 'application/pdf':
                    rec.is_pdf = True
                else:
                    rec.is_pdf = False
            else:
                raise UserError(_('No attachment found!'))

    def merge_selected_pdfs(self):
        # print('Starting PDF merge process')
        merger = PdfFileMerger()
        for record in self:
            for attachment in record.pdf_attachment_ids:
                # print(f'Merging PDF from attachment: {attachment.name}')
                # Decode the PDF file content
                file_content = base64.b64decode(attachment.datas)
                file_stream = io.BytesIO(file_content)
                try:
                    merger.append(file_stream)
                except Exception as e:
                    # print(f'Error appending PDF: {e}')
                    continue

        # Create a merged PDF
        merged_stream = io.BytesIO()
        merger.write(merged_stream)
        merged_stream.seek(0)
        merged_pdf_content = base64.b64encode(merged_stream.read())
        self.write({'merged_pdf': merged_pdf_content})

        # print('PDF merge process completed')
        merger.close()

        return True

    def create_knowledge_article_from_kanban(self):
        self.ensure_one()

        google_url = 'https://www.google.com'

        # Construct the HTML button with proper formatting
        button_html = f'<button type="button" onclick="window.open(\'{google_url}\', \'_blank\')">Open Google</button>'

        article_vals = {
            'name': f'PDF Document: {self.name}',
            'body': button_html,  # Pass HTML content directly
        }

        article = self.env['knowledge.article'].create(article_vals)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'knowledge.article',
            'view_mode': 'form',
            'res_id': article.id,
            'target': 'new',
        }


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    document_ids = fields.Many2many(
        'product.document',
        'product_document_product_template_rel',  # the relation table name
        string="Documents"
    )