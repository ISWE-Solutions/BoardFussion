# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DocumentsFolder(models.Model):
    _inherit = 'documents.folder'
    
    committee_id = fields.Many2one('hr.department', string="Committee")
