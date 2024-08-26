from PyPDF2 import PdfFileMerger
from odoo.exceptions import UserError
import base64
import io
from markupsafe import Markup
from odoo.tools.safe_eval import safe_eval
from odoo.tools import html_escape
from odoo import models, fields, api


class ProductDocument(models.Model):
    _inherit = 'product.document'

    pdf_attachment_ids = fields.Many2many('ir.attachment', string='PDF Files')
    merged_pdf = fields.Binary(string='Merged PDF', readonly=True)
    product_document_id = fields.Many2one('product.document', string='Document ID')
    shown_on_product_page = fields.Boolean(default=True, store=True)
    user_ids = fields.Many2many('res.users')
    partner_ids = fields.Many2many('res.partner')
    ir_attachment_custom_id = fields.Many2one('ir.attachment')

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
