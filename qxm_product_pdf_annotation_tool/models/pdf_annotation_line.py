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
    reply_ids = fields.One2many('pdf.reply.annotation', 'annotation_id', string='Replies')
    document_id = fields.Many2one('product.document', string='Document')

class PdfReplyAnnotation(models.Model):
    _name = 'pdf.reply.annotation'
    _description = 'Replies For Annotation Lines'

    annotation_id = fields.Many2one('product.pdf.annotation.line', string='Annotation', ondelete='cascade')
    reply = fields.Text(string='Reply')
    unique_button = fields.Char('Unique Button Id')
    delete_unique_button = fields.Char('Delete Unique Button Id')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)

