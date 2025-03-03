from odoo import http
from odoo.http import request


class PDFViewerController(http.Controller):

    @http.route('/pdf/viewer/<int:doc_id>', type='http', auth='user', website=True)
    def view_pdf(self, doc_id, **kwargs):
        """Fetch PDF document and render it in the custom viewer."""
        attachment = request.env['ir.attachment'].browse(doc_id)
        if not attachment.exists():
            return request.not_found()

        pdf_url = f'/web/content/{doc_id}?download=false'

        return request.render('custom_pdf_viewer.template_pdf_viewer', {
            'pdf_url': pdf_url,
        })
