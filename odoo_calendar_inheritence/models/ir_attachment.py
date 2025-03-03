from odoo import fields, api, models, _

class Ir_Attachment(models.Model):
    _inherit = 'ir.attachment'

    def unlink(self):
        # print("Executed!")
        res = super(Ir_Attachment, self).unlink()
        return res

    def action_open_pdf(self):
        """Override the default document preview action to open in PDF.js"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/pdf/viewer/{self.id}',
            'target': 'new',
        }