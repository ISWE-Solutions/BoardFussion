from odoo import models, fields

class ProductPDFAnnotationHighlight(models.Model):
    _name = 'product.pdf.annotation.highlight'
    _description = 'PDF Annotation Highlight'

    page_no = fields.Char('Page Number')
    layerx = fields.Char('X Position')
    layery = fields.Char('Y Position')
    width = fields.Char('Width')
    height = fields.Char('Height')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    document_id = fields.Many2one('product.document', 'Document')
    ir_document_id = fields.Many2one('ir.attachment', 'Document')