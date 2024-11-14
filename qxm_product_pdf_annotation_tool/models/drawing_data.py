from odoo import models, fields, api

class DrawingData(models.Model):
    _name='drawing.data'
    _description='Drawing Data'

    page_no = fields.Char('Page No')
    drawing_data = fields.Text(string="Drawing Data")
    document_id = fields.Many2one('product.document', string="Document")

    @api.model
    def save_drawing_data(self, record_id, drawing_data):
        record = self.browse(record_id)
        record.drawing_data = drawing_data
        return True

    @api.model
    def get_drawing_data(self, record_id):
        record = self.browse(record_id)
        return record.drawing_data
