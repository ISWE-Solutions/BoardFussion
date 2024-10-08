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
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    document_id = fields.Many2one('product.document', string='Document')
