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

    @api.onchange('partner_ids')
    def _onchange_partner_ids(self):
        """
        Ensure changes to `partner_ids` are reflected in `Restricted` of related `calendar.event.product.line` records.
        """
        if not self.partner_ids:
            return

        # Find related calendar event product lines
        product_lines = self.env['calendar.event.product.line'].search([
            ('product_document_id', '=', self.id)
        ])
        for line in product_lines:
            line.Restricted = self.partner_ids


    #
    # def write(self, vals):
    #     _logger.info(f"Writing to ProductDocument with IDs {self.ids}. Incoming vals: {vals}")
    #
    #     if self.env.context.get('prevent_recursion'):
    #         _logger.warning("Preventing recursion in ProductDocument.write")
    #         return super(ProductDocument, self).write(vals)
    #
    #     # Use a context flag to prevent recursion
    #     context_with_flag = dict(self.env.context, prevent_recursion=True)
    #
    #     if 'partner_ids' in vals:
    #         # Log current values before update
    #         for document in self:
    #             partner_names_before = document.partner_ids.mapped('name')
    #             user_names_before = document.user_ids.mapped('name')
    #             _logger.info(f"Before update, partner_ids for ProductDocument ID {document.id}: {partner_names_before}")
    #             _logger.info(f"Before update, user_ids for ProductDocument ID {document.id}: {user_names_before}")
    #
    #     res = super(ProductDocument, self.with_context(context_with_flag)).write(vals)
    #
    #     if 'partner_ids' in vals:
    #         for document in self:
    #             partner_names_after = document.partner_ids.mapped('name')
    #             _logger.info(f"After update, partner_ids for ProductDocument ID {document.id}: {partner_names_after}")
    #
    #             # Update and log related CalendarEventProductLine records
    #             product_line_ids = self.env['calendar.event.product.line'].search(
    #                 [('product_document_id', '=', document.id)]
    #             )
    #             _logger.info(f"Found related CalendarEventProductLine records: {product_line_ids.ids}")
    #
    #             for line in product_line_ids:
    #                 restricted_before = line.Restricted.mapped('name')
    #                 # Recompute Restricted field
    #                 line._compute_restricted_attendees()
    #                 restricted_after = line.Restricted.mapped('name')
    #                 _logger.info(f"Restricted before for CalendarEventProductLine ID {line.id}: {restricted_before}")
    #                 _logger.info(f"Restricted after for CalendarEventProductLine ID {line.id}: {restricted_after}")
    #
    #     return res
    #
    # @api.model
    # def create(self, vals):
    #     _logger.info(f"Creating a new ProductDocument. Incoming vals: {vals}")
    #
    #     res = super(ProductDocument, self).create(vals)
    #
    #     if 'partner_ids' in vals:
    #         partner_names = res.partner_ids.mapped('name')
    #         user_names = res.user_ids.mapped('name')
    #         _logger.info(f"After creation, partner_ids for ProductDocument ID {res.id}: {partner_names}")
    #         _logger.info(f"After creation, user_ids for ProductDocument ID {res.id}: {user_names}")
    #
    #         # Update and log related CalendarEventProductLine records
    #         product_line_ids = self.env['calendar.event.product.line'].search(
    #             [('product_document_id', '=', res.id)]
    #         )
    #         _logger.info(f"Found related CalendarEventProductLine records for new ProductDocument: {product_line_ids.ids}")
    #
    #         for line in product_line_ids:
    #             restricted_before = line.Restricted.mapped('name')
    #             line.Restricted = res.partner_ids
    #             restricted_after = line.Restricted.mapped('name')
    #             _logger.info(f"Restricted before for CalendarEventProductLine ID {line.id}: {restricted_before}")
    #             _logger.info(f"Restricted after for CalendarEventProductLine ID {line.id}: {restricted_after}")
    #
    #     return res

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