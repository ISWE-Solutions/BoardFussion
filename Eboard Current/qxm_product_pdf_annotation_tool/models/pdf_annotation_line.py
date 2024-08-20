# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductPDFAnnotationLine(models.Model):
    _name = 'product.pdf.annotation.line'
    _description = 'Product PDF Annotation Line'

    page_no = fields.Char('Page No')
    layerx = fields.Char(string='LayerX')
    layery = fields.Char(string='LayerY')
    description = fields.Char(string='Description')
    document_id = fields.Many2one('product.document', string='Document')
