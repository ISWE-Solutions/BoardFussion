from odoo import models, fields, api, _


class VideoAttachment(models.Model):
    """Vehicle Damage Image"""
    _name = "video.attachment"

    avatar = fields.Many2many(comodel_name="ir.attachment", string="Videos")
    video_description = fields.Text(string="Description")
    calendar_id = fields.Many2one('calendar.event')