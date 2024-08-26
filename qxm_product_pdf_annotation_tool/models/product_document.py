# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models

class ProductDocument(models.Model):
    _inherit = 'product.document'

    def action_open_pdf_annotation(self):
        self.ensure_one()
        return {
                'name':self.display_name or 'Product PDF Annotation',
                'type': 'ir.actions.client',
                'tag': 'qxm_product_pdf_annotation_tool.product_pdf_annotation',
                'target': 'current',
                'params': {},
            }

    def action_view_pdf_annotation(self):
        return {
            'name': self.display_name or 'Preview PDF Annotation',
            'type': 'ir.actions.client',
            'tag': 'qxm_product_pdf_annotation_tool.pdf_custom_preview',
            'target': 'current',
            'params': {},
        }

    def get_document_data(self):
        data = self.sudo().read()
        lines = self.env['product.pdf.annotation.line'].sudo().search_read([('document_id', '=', self.sudo().id)], [])
        lines = {page: [item for item in lines if item['page_no'] == page] for page in set(item['page_no'] for item in lines)}
        return {'pdf':data[0] if data else {}, 'lines':lines}
