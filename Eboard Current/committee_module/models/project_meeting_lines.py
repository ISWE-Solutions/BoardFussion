# from markupsafe import Markup
# from odoo import models, fields, _, api
# from odoo.exceptions import ValidationError
#
#
# class CalendarEventProductLine(models.Model):
#     _name = ''
#     _description = 'Calendar Event Product Line'
#     _order = 'sequence'
#
#     sequence = fields.Integer(string='Sequence', default=10)
#     calendar_id = fields.Many2one('calendar.event', string="Calendar Event")
#     product_id = fields.Many2one('product.template', string="Product")
#     quantity = fields.Float(string="Quantity")
#     uom_id = fields.Many2one('uom.uom', string="Unit of Measure")
#     agenda = fields.Char(string='Agenda', default=_('new'))
#     presenter_id = fields.Many2many('hr.employee', string="Presenter", tracking=True)
#     duration = fields.Float(string="Duration")
#     start_date = fields.Datetime(string='Start Date', default=lambda self: fields.Datetime.now())
#     end_date = fields.Datetime(string='End Date')
#     description = fields.Html(string='Description')
#     time = fields.Char(string='Time')