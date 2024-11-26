from odoo import models, fields

class PdfHighlightMarker(models.Model):
    _name = 'pdf.highlight.marker'
    _description = 'PDF Highlight Marker'

    page_no = fields.Char('Page Number')
    layerx = fields.Char('X Position')
    layery = fields.Char('Y Position')
    width = fields.Char('Width')
    height = fields.Char('Height')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    document_id = fields.Many2one('product.document', 'Document', ondelete='cascade')