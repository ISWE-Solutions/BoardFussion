from odoo import fields, api, models, _

class Ir_Attachment(models.Model):
    _inherit = 'ir.attachment'

    def unlink(self):
        print("Executed!")
        res = super(Ir_Attachment, self).unlink()
        return res